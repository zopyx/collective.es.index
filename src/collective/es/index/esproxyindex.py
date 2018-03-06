# -*- coding: utf-8 -*-
from AccessControl import ClassSecurityInfo
from AccessControl.requestmethod import postonly
from BTrees.IIBTree import IISet
from collective.es.index.utils import get_query_client
from collective.es.index.utils import index_name
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.GenericSetup.interfaces import ISetupEnviron
from Products.GenericSetup.utils import NodeAdapterBase
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PluginIndexes.interfaces import ISortIndex
from zope.component import adapter
from zope.interface import implementer

import jinja2
import json
import logging


logger = logging.getLogger(__name__)

jinja_loader = jinja2.Environment(loader=jinja2.BaseLoader)

VIEW_PERMISSION = 'View'
MGMT_PERMISSION = 'Manage ZCatalogIndex Entries'

manage_addESPIndexForm = PageTemplateFile('www/addIndex', globals())

BATCH_SIZE = 500


# Hint for my future self: When copying this code, never name it
# manage_addIndex here. Otherwise install will be broken.
# There is some serious namespace pollution in Zope.App.FactoryDispatcher

def manage_addESPIndex(
    context,
    id,
    extra=None,
    REQUEST=None,
    RESPONSE=None,
    URL3=None,
):
    """Adds a date range in range index"""
    result = context.manage_addIndex(
        id,
        'ElasticSearchProxyIndex',
        extra=extra,
        REQUEST=REQUEST,
        RESPONSE=RESPONSE,
        URL1=URL3,
    )
    return result


@implementer(ISortIndex)
class ElasticSearchProxyIndex(SimpleItem):
    meta_type = 'ElasticSearchProxyIndex'
    security = ClassSecurityInfo()

    manage_main = PageTemplateFile('www/manageIndex', globals())
    manage_options = (
        {
            'label': 'Settings',
            'action': 'manage_main',
        },
    )

    def __init__(
        self,
        id,
        ignore_ex=None,
        call_methods=None,
        extra=None,
        caller=None,
    ):
        self.id = id
        self.caller = caller
        if extra is None:
            return
        try:
            self.query_template = extra.query_template
        except AttributeError:
            try:
                # alternative: allow a dict (lowers bootstrapping effort
                # from code)
                self.query_template = extra['query_template']
            except KeyError:
                raise ValueError(
                    'ElasticSearchProxyIndex needs "extra" kwarg with key or '
                    'attribute "query_template".',
                )

    @security.protected(MGMT_PERMISSION)
    @postonly
    def manage_ESPIndexExtras(self, REQUEST):
        """stores changed extras """
        self.query_template = REQUEST.form['extra']['query_template']
        REQUEST['RESPONSE'].redirect(
            '{0}/manage_catalogIndexes?manage_tabs_message=Updated '
            'index settings for {1}'.format(
                self.aq_parent.absolute_url(),
                self.id,
            ),
        )

    ###########################################################################
    # Methods we dont need to implement, from IPluginIndex.
    # Those operations are done in the queue processor in a more efficinet way.
    ###########################################################################

    def index_object(self, documentId, obj, threshold=None):
        pass

    def unindex_object(self, documentId):
        pass

    def clear(self):
        pass

    ###########################################################################
    #  methods from IPluginIndex
    ###########################################################################

    def getEntryForObject(self, documentId, default=None):
        """Get all information contained for 'documentId'.

        We fetch here the tika converted text field from ES and return it.
        """
        # XXX TODO
        return ''

    def getIndexSourceNames(self):
        """Get a sequence of attribute names that are indexed by the index.
        return sequence of indexed attributes

        """
        # Future: here we could fiddle with the ES query to get the attributes.
        #         For now, we just return the index name.
        return [self.id]

    def getIndexQueryNames(self):
        """Get a sequence of query parameter names to which this index applies.

        Note: Needed for query plan.

        Indicate that this index applies to queries for the index's name.
        """
        return (self.id,)

    def _apply_index(self, request):
        """Apply the index to query parameters given in 'request'.

        The argument should be a mapping object.

        If the request does not contain the needed parameters, then
        None is returned.

        If the request contains a parameter with the name of the
        column and this parameter is either a Record or a class
        instance then it is assumed that the parameters of this index
        are passed as attribute (Note: this is the recommended way to
        pass parameters since Zope 2.4)

        Otherwise two objects are returned.  The first object is a
        ResultSet containing the record numbers of the matching
        records.  The second object is a tuple containing the names of
        all data fields used.
        """
        record = parseIndexRequest(request, self.id)
        if record.keys is None:
            return None
        template_params = record.keys[0]
        query_body = self._apply_template(template_params)
        es_kwargs = dict(
            index=index_name(),
            body=query_body,
            size=BATCH_SIZE,
            scroll='1m',
            _source_include=['rid'],
        )
        es = get_query_client()
        result = es.search(**es_kwargs)

        # initial return value, other batches to be applied
        retval = IISet([r['_source']['rid'] for r in result['hits']['hits']])

        total = result['hits']['total']
        if total > BATCH_SIZE:
            sid = result['_scroll_id']
            counter = BATCH_SIZE
            while counter < total:
                result = es.scroll(scroll_id=sid, scroll='1m')
                for record in result['hits']['hits']:
                    retval.append(record['_source']['rid'])
                counter += BATCH_SIZE
        return retval

    def numObjects(self):
        """Return the number of indexed objects."""
        es_kwargs = dict(
            index=index_name(),
            body={'query': {'match_all': {}}},
        )
        es = get_query_client()
        try:
            return es.count(**es_kwargs)['count']
        except Exception:
            logger.exception('ElasticSearch "count" query failed')
            return 'Problem getting all documents count from ElasticSearch!'

    def indexSize(self):
        """Return the size of the index in terms of distinct values."""
        return 'n/a'

    ###########################################################################
    #  methods coming from ISortIndex
    ###########################################################################

    def keyForDocument(documentId):
        """Return the sort key that cooresponds to the specified document id

        This method is no longer used by ZCatalog, but is left for backwards
        compatibility."""
        # We do not implement this BBB method.
        pass

    def documentToKeyMap():
        """Return an object that supports __getitem__ and may be used to
        quickly lookup the sort key given a document id"""

    ###########################################################################
    #  private helper methods
    ###########################################################################

    def _apply_template(self, template_data):
        tpl = jinja_loader.from_string(self.query_template)
        query_text = tpl.render(**template_data)
        return json.loads(query_text)


InitializeClass(ElasticSearchProxyIndex)


@adapter(ElasticSearchProxyIndex, ISetupEnviron)
class IndexNodeAdapter(NodeAdapterBase):
    """Node im- and exporter for Index.
    """

    @property
    def node(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('index')
        container = self._doc.createElement('fields')
        node.appendChild(container)
        for field in self.context.fieldweights:
            child = self._doc.createElement(field)
            child.attributes['weight'] = str(
                self.context.fieldweights['field'],
            )
            container.appendChild(child),
        return node

    @node.setter
    def node(self, node):
        """Import the object from the DOM node.
        """
        self.context.fieldweights = {}
        for field in node['fields'].childnodes:
            value = field.getAttribute('value')
            self.context.fieldweights[field.tagName] = float(value)

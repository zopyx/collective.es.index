# -*- coding: utf-8 -*-
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.GenericSetup.interfaces import ISetupEnviron
from Products.GenericSetup.utils import NodeAdapterBase
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PluginIndexes.interfaces import ISortIndex
from zope.component import adapter
from zope.interface import implementer

import json


VIEW_PERMISSION = 'View'
MGMT_PERMISSION = 'Manage ZCatalogIndex Entries'

manage_addESSTIndexForm = PageTemplateFile('www/addIndex', globals())


def manage_addESSTIndex(
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
        'ESSearchableTextIndex',
        extra=extra,
        REQUEST=REQUEST,
        RESPONSE=RESPONSE,
        URL1=URL3,
    )
    return result


@implementer(ISortIndex)
class ESSearchableTextIndex(SimpleItem):
    meta_type = 'ESSearchableTextIndex'
    security = ClassSecurityInfo()

    manage_options = (
        {
            'label': 'Settings',
            'action': 'manage_main',
        },
    ),
    manage_main = PageTemplateFile('www/manageIndex', globals())

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
                self.fieldweights = extra['query']
            except KeyError:
                raise ValueError(
                    'ESSearchableTextIndex needs \'extra\' kwarg with key or '
                    'attribute \'query_template\'.',
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

        XXX: here we could fiddle with the ES query to get the attributes.
             For now, we just return the index name.
        """
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
        es_query = self._apply_template(record)
        # import pdb; pdb.set_trace()

    def numObjects(self):
        """Return the number of indexed objects."""
        # XXX: figure out how to get all possible candidates for text query
        #      for now all ES indexed object are fine.
        return -1

    def indexSize(self):
        """Return the size of the index in terms of distinct values."""
        # XXX: is this possible with ES? I fear not.
        return -1

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

    def _apply_template(self, template_context):
        query_text = self.query_template.format(template_context)
        return json.loads(query_text)


InitializeClass(ESSearchableTextIndex)


@adapter(ESSearchableTextIndex, ISetupEnviron)
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

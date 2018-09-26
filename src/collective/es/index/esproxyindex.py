# -*- coding: utf-8 -*-
from AccessControl import ClassSecurityInfo
from BTrees.IIBTree import IIBTree
from BTrees.OOBTree import OOBTree
from collective.es.index.utils import get_configuration
from collective.es.index.utils import get_query_client
from collective.es.index.utils import index_name
from collective.es.index.utils import query_blocker
from elasticsearch.exceptions import TransportError
from elasticsearch_dsl import Search
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.CMFCore.interfaces import IIndexQueueProcessor
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PluginIndexes.interfaces import ISortIndex
from zope.annotation.interfaces import IAnnotations
from zope.component import queryUtility
from zope.interface import implementer

import logging


logger = logging.getLogger(__name__)

manage_addESPIndexForm = PageTemplateFile('www/addIndex', globals())

BATCH_SIZE = 500

FRAGMENT_SIZE = 50

SEARCH_FIELDS = ('title^1.2',
                 'description^1.1',
                 'subjects^2',
                 'extracted_text.content',
                 'extracted_file.content',
                 'extracted_image.content',
                 )

HIGHLIGHT_KEY = 'collective.es.index.highlight'


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

    query_options = ('query',)

    manage_main = PageTemplateFile('www/manageIndex', globals())

    def __init__(
        self,
        id,
        ignore_ex=None,
        call_methods=None,
        caller=None,
    ):
        self.id = id
        self.caller = caller

    ###########################################################################
    # Methods we dont need to implement, from IPluginIndex.
    # Those operations are done in the queue processor in a more efficinet way.
    ###########################################################################

    def index_object(self, documentId, obj, threshold=None):
        indexer = queryUtility(IIndexQueueProcessor, name='collective.es.index')
        doc = obj._IndexableObjectWrapper__object
        indexer.index(doc)
        return 0

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
        config = get_configuration()
        timeout = getattr(config, 'request_timeout', 20)
        if query_blocker.blocked:
            return
        record = parseIndexRequest(request, self.id)
        if record.keys is None:
            return None
        es = get_query_client()
        search = Search(using=es, index=index_name())
        search = search.params(request_timeout=timeout,
                               size=BATCH_SIZE,
                               preserve_order=True,
                               )
        search = search.source(include='rid')
        query_string = record.keys[0].decode('utf8')
        if query_string and query_string.startswith('*'):
            # plone.app.querystring contains op sends a leading *, remove it
            query_string = query_string[1:]
        search = search.query('simple_query_string',
                              query=query_string,
                              fields=SEARCH_FIELDS
                              )
        # setup highlighting
        for field in SEARCH_FIELDS:
            name = field.split('^')[0]
            if name == 'title':
                # title shows up in results anyway
                continue
            search = search.highlight(name, fragment_size=FRAGMENT_SIZE)

        try:
            result = search.scan()
        except TransportError:
            # No es client, return empty results
            logger.exception('ElasticSearch client not available.')
            return IIBTree(), (self.id,)
        # initial return value, other batches to be applied

        retval = IIBTree()
        highlights = OOBTree()
        for r in result:
            retval[r.rid] = int(10000 * float(r.meta.score))
            # Index query returns only rids, so we need
            # to save highlights for later use
            highlight_list = []
            if getattr(r.meta, 'highlight', None) is not None:
                for key in dir(r.meta.highlight):
                    highlight_list.extend(r.meta.highlight[key])
            highlights[r.meta.id] = highlight_list

        # store highlights
        try:
            annotations = IAnnotations(self.REQUEST)
            annotations[HIGHLIGHT_KEY] = highlights
        except TypeError:
            # maybe we are in a test
            pass

        return retval, (self.id,)

    def numObjects(self):
        """Return the number of indexed objects."""
        es = get_query_client()
        search = Search(using=es, index=index_name())
        try:
            return len(list(search.scan()))
        except Exception:
            logger.exception('ElasticSearch "count" query failed')
            return 'Problem getting all documents count from ElasticSearch!'

    def indexSize(self):
        """Return the size of the index in terms of distinct values."""
        return 'n/a'

    ###########################################################################
    #  methods coming from ISortIndex
    ###########################################################################

    def keyForDocument(self, documentId):
        """Return the sort key that cooresponds to the specified document id

        This method is no longer used by ZCatalog, but is left for backwards
        compatibility."""
        # We do not implement this BBB method.
        pass

    def documentToKeyMap(self):
        """Return an object that supports __getitem__ and may be used to
        quickly lookup the sort key given a document id"""

        # We can not implement this afaik


InitializeClass(ElasticSearchProxyIndex)

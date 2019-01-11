# -*- coding: utf-8 -*-
import DateTime
from zope.component import getMultiAdapter

from elasticsearch_dsl import Search
from elasticsearch_dsl import FacetedSearch
from elasticsearch_dsl import DateHistogramFacet
from elasticsearch_dsl import HistogramFacet
from elasticsearch_dsl import RangeFacet
from elasticsearch_dsl import TermsFacet
from elasticsearch_dsl.faceted_search import FacetedResponse

from plone.app.contentlisting.interfaces import IContentListingObject
from Products.CMFPlone.PloneBatch import Batch
from Products.CMFPlone.utils import getToolByName
from Products.Five.browser import BrowserView

from collective.es.index.esproxyindex import SEARCH_FIELDS
from collective.es.index.esproxyindex import BATCH_SIZE
from collective.es.index.utils import get_configuration
from collective.es.index.utils import get_query_client
from collective.es.index.utils import index_name


DEFAULT_FACETS = {
    'subjects': TermsFacet(field='subjects.keyword'),
    'review_state': TermsFacet(field='review_state.keyword'),
    'modified': DateHistogramFacet(field='modified', interval='month'),
}

DATE_INTERVALS = ['month', 'week', 'day', 'hour']

DATE_FORMATS = {
    'month': '%B %Y',
    'week': 'Week of %b %-d, %Y',
    'day': '%B %-d, %Y',
    'hour': '%b %-d %-I %p',
}


def get_configured_facets():
    facets = None
    configuration = get_configuration()
    if configuration and hasattr(configuration, 'facets'):
            facets = configuration.facets.split()
    if facets:
        configured_facets = {}
        for facet in facets:
            if ',' in facet:
                field, interval = facet.split(',', 1)
                if ',' in interval:
                    intervals = interval.split(',')
                    ranges = []
                    for interval in intervals:
                        name, numbers = interval.split(':')
                        numbers = numbers.split('-')
                        irange = []
                        for number in numbers:
                            if number.lower() == 'none':
                                irange.append(None)
                            else:
                                try:
                                    irange.append(int(number))
                                except ValueError:
                                    continue
                        irange = tuple(irange)
                        ranges.append((name, irange))
                    configured_facets[field] = RangeFacet(field=field,
                                                          ranges=ranges)
                elif interval in DATE_INTERVALS:
                    configured_facets[field] = DateHistogramFacet(field=field,
                                                                  interval=interval)
                else:
                    try:
                        interval = int(interval)
                        configured_facets[field] = HistogramFacet(field=field,
                                                                  interval=interval)
                    except ValueError:
                        pass
            else:
                configured_facets[facet] = TermsFacet(field=facet + '.keyword')
    else:
        configured_facets = DEFAULT_FACETS
    return configured_facets


def get_search_fields():
    configuration = get_configuration()
    search_fields = getattr(configuration, 'search_fields', None)
    if not search_fields:
        search_fields = SEARCH_FIELDS
    return search_fields.split()


class PloneSearch(FacetedSearch):

    fields = get_search_fields()

    facets = get_configured_facets()

    def search(self):
        es = get_query_client()
        s = Search(doc_type=self.doc_types, index=index_name(), using=es)
        s = s.params(size=BATCH_SIZE)
        return s.response_class(FacetedResponse)

    def query(self, search, query):
        if query:
            return search.query('simple_query_string',
                                fields=self.fields,
                                query=query)
        return search


class FacetedPloneSearch(BrowserView):

    _facets = []

    def navroot_url(self):
        if not hasattr(self, '_navroot_url'):
            state = self.context.unrestrictedTraverse('@@plone_portal_state')
            self._navroot_url = state.navigation_root_url()
        return self._navroot_url

    def breadcrumbs(self, item):
        obj = item.getObject()
        view = getMultiAdapter((obj, self.request), name='breadcrumbs_view')
        breadcrumbs = list(view.breadcrumbs())[:-1]
        if len(breadcrumbs) == 0:
            return None
        if len(breadcrumbs) > 3:
            empty = {'absolute_url': '', 'Title': unicode('…', 'utf-8')}
            breadcrumbs = [breadcrumbs[0], empty] + breadcrumbs[-2:]
        return breadcrumbs

    def get_filters(self, facets=None):
        query = self.request.get('query', '*')
        filters = {}
        if facets is not None:
            for facet in facets:
                filter = self.request.get(facet, None)
                if filter is not None:
                    if facets[facet].agg_type == 'date_histogram':
                        if isinstance(filter, list):
                            filters[facet] = [DateTime.DateTime(f).asdatetime()
                                              for f in filter]
                        else:
                            filters[facet] = DateTime.DateTime(filter).asdatetime()
                    elif facets[facet].agg_type == 'histogram':
                        if isinstance(filter, list):
                            filters[facet] = [int(float(f)) for f in filter]
                        else:
                            filters[facet] = int(float(filter))
                    elif facets[facet].agg_type == 'range':
                        if isinstance(filter, list):
                            filters[facet] = [int(float(f)) for f in filter]
                        else:
                            filters[facet] = int(float(filter))
                    else:
                        filters[facet] = filter
        return query, filters

    def format_value(self, facet, value):
        facet = PloneSearch.facets[facet]
        if facet.agg_type == 'date_histogram':
            dformat = facet._params['interval']
            value = value.strftime(DATE_FORMATS[dformat])
        return value

    def results(self, b_size=10, b_start=0):
        catalog = getToolByName(self.context, 'portal_catalog')
        query, filters = self.get_filters(facets=PloneSearch.facets)
        search = PloneSearch(query, filters=filters)
        response = search.execute()
        self._facets = response.facets
        hits = [hit._d_['rid'] for hit in response.hits
                if 'rid' in hit._d_]
        brains = [IContentListingObject(catalog._catalog[rid]) for rid in hits]
        batch = Batch(brains, b_size, b_start)
        return batch

    def facets(self):
        return self._facets

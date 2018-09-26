# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchClient
from plone import api
from plone.api.exc import CannotGetPortalError
from zope.component import queryUtility

import threading


INDEX = 'plone'

_block_es_queries = threading.local()


def _get_elastic_search_client():
    return queryUtility(IElasticSearchClient)


def get_query_client():
    """ES Clients for queries
    """
    es = _get_elastic_search_client()
    if es:
        return es


def get_ingest_client():
    """ES Clients for adding, modifing or deleting
    """
    es = _get_elastic_search_client()
    if es:
        return es.ingest


def get_configuration():
    """Get zope.conf elasticsearch configuration
    """
    es = _get_elastic_search_client()
    if es:
        return es.zope_configuration


def remove_index(index=INDEX):
    es = get_ingest_client()
    if es.indices.exists(index=index):
        es.indices.delete(index=index)


def index_name():
    try:
        portal = api.portal.get()
        name = 'plone_{0}'.format(portal.getId()).lower()
    except CannotGetPortalError:
        # portal is being unindexed
        name = None
    return name


class _QueryBlocker(object):

    @property
    def blocked(self):
        return getattr(_block_es_queries, 'blocked', False)

    def block(self):
        return setattr(_block_es_queries, 'blocked', True)

    def unblock(self):
        return setattr(_block_es_queries, 'blocked', False)


query_blocker = _QueryBlocker()

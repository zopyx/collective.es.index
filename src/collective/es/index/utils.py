# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchClient
from plone import api
from zope.component import queryUtility

import logging
import threading


logger = logging.getLogger(__name__)

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


def remove_index():
    es = get_ingest_client()
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)


def index_name():
    portal = api.portal.get()
    return 'plone_{0}'.format(portal.getId()).lower()


class _QueryBlocker(object):

    @property
    def blocked(self):
        return getattr(_block_es_queries, 'blocked', False)

    def block(self):
        return setattr(_block_es_queries, 'blocked', True)

    def unblock(self):
        return setattr(_block_es_queries, 'blocked', False)


query_blocker = _QueryBlocker()

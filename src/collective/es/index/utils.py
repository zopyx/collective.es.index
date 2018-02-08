# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchClientProvider
from zope.component import queryUtility

import logging

logger = logging.getLogger(__name__)

INDEX = 'plone'


def _get_elastic_search_client_provider():
    return queryUtility(IElasticSearchClientProvider)


def get_query_client():
    """ES Clients for queries
    """
    escp = _get_elastic_search_client_provider()
    if escp:
        return escp.query


def get_ingest_client():
    """ES Clients for adding, modifing or deleting
    """
    escp = _get_elastic_search_client_provider()
    if escp:
        return escp.ingest


def remove_index():
    es = get_ingest_client()
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)

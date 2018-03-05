# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchClient
from plone import api
from zope.component import queryUtility

import logging


logger = logging.getLogger(__name__)

INDEX = 'plone'


def _get_elastic_search_client():
    return queryUtility(IElasticSearchClient)


def get_query_client():
    """ES Clients for queries
    """
    es = _get_elastic_search_client()
    if es:
        return es.query


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


def index_name(self):
    portal = api.portal.get()
    return 'plone_{0}'.format(portal.getId()).lower()

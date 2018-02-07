# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchClientProvider
from plone import api
from zope.component import getUtility

import logging

logger = logging.getLogger(__name__)

INDEX = 'plone'


def get_query_client():
    """ES Clients for queries
    """
    return getUtility(IElasticSearchClientProvider).query


def get_ingress_client():
    """ES Clients for adding, modifing or deleting
    """
    return getUtility(IElasticSearchClientProvider).ingress


def remove_index():
    es = get_ingress_client()
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)


def index_document(context):
    data = {'todo': 'todo'}
    uid = api.content.get_uuid(context)
    try:
        es = get_ingress_client()
        es.index(
            index=INDEX,
            doc_type=context.portal_type,
            id=uid,
            body=data,
        )
    except Exception:
        logger.exception('indexing of {0} failed'.format(uid))


def unindex_document(context):
    uid = api.content.get_uuid(context)
    try:
        es = get_ingress_client()
        es.delete(
            index=INDEX,
            doc_type=context.portal_type,
            id=uid,
        )
    except Exception:
        logger.exception('indexing of {0} failed'.format(uid))

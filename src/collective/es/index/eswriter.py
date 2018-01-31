# -*- coding: utf-8 -*-
from plone import api

import logging

logger = logging.getLogger(__name__)

INDEX = 'plone'


def get_client():
    """ES Client
    """


def remove_index():
    es = get_client()
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)


def index_document(context):
    data = {'todo': 'todo'}
    uid = api.content.get_uuid(context)
    try:
        es = get_client()
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
        es = get_client()
        es.delete(
            index=INDEX,
            doc_type=context.portal_type,
            id=uid,
        )
    except Exception:
        logger.exception('indexing of {0} failed'.format(uid))

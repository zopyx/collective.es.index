# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchIndexQueueProcessor
from elasticsearch import Elasticsearch
from plone import api
from zope.interface import implementer

import logging

logger = logging.getLogger('collective.es.index')


@implementer(IElasticSearchIndexQueueProcessor)
class ElasticSearchIndexQueueProcessor(object):
    """ a queue processor for ElasticSearch"""

    def index(self, obj, attributes=None):
        es = self.get_es_client()
        if es is None:
            logger.warning(
                'No ElasticSearch client available.'
            )
            return
        data = {'todo': 'todo'}
        uid = api.content.get_uuid(obj)
        try:
            es.index(
                index=self.es_index_name,
                doc_type=obj.portal_type,
                parent='',
                id=uid,
                body=data,
            )
        except Exception:
            logger.exception('indexing of {0} failed'.format(uid))

    def reindex(self, obj, attributes=None):
        self.index(obj, attributes)

    def unindex(self, obj):
        es = self.get_es_client()
        if es is None:
            logger.warning(
                'No ElasticSearch client available.'
            )
            return
        uid = api.content.get_uuid(obj)
        try:
            es.delete(
                index=self.index,
                doc_type=obj.portal_type,
                id=uid,
            )
        except Exception:
            logger.exception('unindexing of {0} failed'.format(uid))

    def begin(self):
        pass

    def commit(self, wait=None):
        pass

    def abort(self):
        pass

    # helper methods
    def get_es_client(self):
        return Elasticsearch(
            [
                {
                    'host': 'localhost',
                    'port': '9200'
                }
            ]
        )

    @property
    def es_index_name(self):
        portal = api.portal.get()
        return 'plone_{0}'.format(portal.getId())

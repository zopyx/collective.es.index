# -*- coding: utf-8 -*-
from Acquisition import aq_base
from Acquisition import aq_parent
from collective.es.index.interfaces import IElasticSearchIndexQueueProcessor
from collective.es.index.utils import get_ingest_client
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone.restapi.interfaces import ISerializeToJson
from zope.interface import implementer
from zope.component import getMultiAdapter
from zope.globalrequest import getRequest

import logging

logger = logging.getLogger('collective.es.index')


@implementer(IElasticSearchIndexQueueProcessor)
class ElasticSearchIndexQueueProcessor(object):
    """ a queue processor for ElasticSearch"""

    def index(self, obj, attributes=None):
        es = get_ingest_client()
        if es is None:
            logger.warning(
                'No ElasticSearch client available.'
            )
            return
        serializer = getMultiAdapter((obj, getRequest()), ISerializeToJson)
        data = serializer()
        uid = api.content.get_uuid(obj)
        es_kwargs = dict(
            index=self._es_index_name,
            doc_type='content',  # XXX why do we still need it in ES6+?
            id=uid,
            body=data,
        )
        # parent = aq_parent(obj)
        # if aq_base(IPloneSiteRoot(obj)) is not aq_base(parent):
        # todo: update es_kwargs with parent data
        #    pass
        try:
            es.index(**es_kwargs)
        except Exception:
            logger.exception('indexing of {0} failed'.format(uid))

    def reindex(self, obj, attributes=None, update_metadata=1):
        self.index(obj, attributes)

    def unindex(self, obj):
        es = get_ingest_client()
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

    @property
    def _es_index_name(self):
        portal = api.portal.get()
        return 'plone_{0}'.format(portal.getId()).lower()

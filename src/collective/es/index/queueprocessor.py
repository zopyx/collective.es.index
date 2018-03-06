# -*- coding: utf-8 -*-
from Acquisition import aq_base
from Acquisition import aq_parent
from collective.es.index.interfaces import IElasticSearchIndexQueueProcessor
from collective.es.index.utils import get_ingest_client
from collective.es.index.utils import index_name
from elasticsearch.exceptions import NotFoundError
from plone import api
from plone.app.textfield.interfaces import IRichTextValue
from plone.memoize import ram
from plone.namedfile.interfaces import IBlobby
from plone.restapi.interfaces import ISerializeToJson
from zope.annotation import IAnnotations
from zope.component import getMultiAdapter
from zope.globalrequest import getRequest
from zope.interface import implementer

import base64
import logging
import uuid


logger = logging.getLogger('collective.es.index')


ES_PORTAL_UUID_KEY = 'collective.es.index.portal_uuid'


KEYS_TO_REMOVE = [
    'items',
    'items_total',
    'parent',
]

INGEST_PIPELINES = {
    'description': 'Extract Plone Binary attachment information',
    'processors': [
        {
            'attachment': {
                'field': 'text',
                'target_field': 'extracted_text',
                'ignore_missing': True,
            },
        },
        {
            'attachment': {
                'field': 'file',
                'target_field': 'extracted_file',
                'ignore_missing': True,
            },
        },
        {
            'attachment': {
                'field': 'image',
                'target_field': 'extracted_image',
                'ignore_missing': True,
            },
        },
    ],
}


@implementer(IElasticSearchIndexQueueProcessor)
class ElasticSearchIndexQueueProcessor(object):
    """ a queue processor for ElasticSearch"""

    def _check_and_add_portal_to_index(self, portal):
        # at first portal is not in ES!
        # Also, portal has no UUID. bad enough. so for es we give it one.
        # If portal has our UUID we assume it is also indexed already
        annotations = IAnnotations(portal)
        if ES_PORTAL_UUID_KEY in annotations:
            # looks like we're indexed.
            return

        annotations[ES_PORTAL_UUID_KEY] = uid = uuid.uuid4().hex
        serializer = getMultiAdapter((portal, getRequest()), ISerializeToJson)
        data = serializer()
        self._reduce_data(data)
        es_kwargs = dict(
            index=index_name(),
            doc_type='content',  # XXX why do we still need it in ES6+?
            id=uid,
            body=data,
        )
        es = get_ingest_client()
        try:
            es.index(**es_kwargs)
        except Exception:
            logger.exception('indexing of {0} failed'.format(uid))

    def _reduce_data(self, data):
        for key in KEYS_TO_REMOVE:
            if key in data:
                del data[key]

    def _iterate_binary_fields(self, obj, data):
        for record in INGEST_PIPELINES['processors']:
            yield record['attachment']['field']

    def _expand_binary_data(self, obj, data):
        for fieldname in self._iterate_binary_fields(obj, data):
            if fieldname not in data:
                continue
            field = getattr(obj, fieldname, None)
            if field is None:
                continue
            data[fieldname + '_meta'] = data[fieldname]
            if IBlobby.providedBy(field):
                with field.open() as fh:
                    data[fieldname] = base64.b64encode(fh.read())
            elif IRichTextValue.providedBy(field):
                data[fieldname] = base64.b64encode(
                    data[fieldname + '_meta']['data'].encode('utf8'),
                )

    def _expand_rid(self, obj, data):
        cat = api.portal.get_tool('portal_catalog')
        path = '/'.join(obj.getPhysicalPath())
        data['rid'] = cat.getrid(path)

    def index(self, obj, attributes=None):
        es = get_ingest_client()
        if es is None:
            logger.warning(
                'No ElasticSearch client available.',
            )
            return
        self._check_for_ingest_pipeline(es)
        serializer = getMultiAdapter((obj, getRequest()), ISerializeToJson)
        data = serializer()
        self._reduce_data(data)
        self._expand_rid(obj, data)
        self._expand_binary_data(obj, data)
        uid = api.content.get_uuid(obj)
        es_kwargs = dict(
            index=index_name(),
            doc_type='content',  # XXX why do we still need it in ES6+?
            id=uid,
            pipeline=self._es_pipeline_name,
            body=data,
        )
        parent = aq_parent(obj)
        portal = api.portal.get()
        if aq_base(portal) is aq_base(parent):
            self._check_and_add_portal_to_index(portal)
            # annotations = IAnnotations(portal)
            # es_kwargs['parent'] = annotations[ES_PORTAL_UUID_KEY]
            pass
        else:
            # es_kwargs['parent'] = api.content.get_uuid(parent)
            pass
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
                'No ElasticSearch client available.',
            )
            return
        uid = api.content.get_uuid(obj)
        try:
            es.delete(
                index=index_name(),
                doc_type='content',  # XXX why do we still need it in ES6+?
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
    def _es_pipeline_name(self):
        return 'attachment_ingest_{0}'.format(index_name())

    @ram.cache(lambda *args: index_name())
    def _check_for_ingest_pipeline(self, es):
        # do we have the ingest pipeline?
        try:
            es.ingest.get_pipeline(self._es_pipeline_name)
        except NotFoundError:
            es.ingest.put_pipeline(self._es_pipeline_name, INGEST_PIPELINES)

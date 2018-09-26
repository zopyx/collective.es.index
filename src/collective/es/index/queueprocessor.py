# -*- coding: utf-8 -*-
from Acquisition import aq_base
from Acquisition import aq_parent
from collective.es.index.interfaces import IElasticSearchIndexQueueProcessor
from collective.es.index.mappings import INITIAL_MAPPING
from collective.es.index.utils import get_configuration
from collective.es.index.utils import get_ingest_client
from collective.es.index.utils import index_name
from collective.es.index.utils import query_blocker
from collective.es.index.tasks import index_content
from collective.es.index.tasks import unindex_content
from elasticsearch.exceptions import NotFoundError
from elasticsearch.exceptions import TransportError
from plone import api
from plone.app.textfield.interfaces import IRichTextValue
from plone.memoize import ram
from plone.namedfile.interfaces import IBlobby
from plone.restapi.interfaces import ISerializeToJson
from pprint import pformat
from zope.annotation import IAnnotations
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.globalrequest import getRequest
from zope.interface import implementer

import base64
import logging
import uuid


es_config = get_configuration()
indexed_chars = getattr(es_config, 'indexed_chars', None)

logger = logging.getLogger(__name__)

ES_PORTAL_UUID_KEY = 'collective.es.index.portal_uuid'
CACHE_ATTRIBUTE = '_collective_elasticsearch_mapping_cache_'


KEYS_TO_REMOVE = [
    'items',
    'items_total',
    'parent',
    '@components',
]

INGEST_PIPELINES = {
    'description': 'Extract Plone Binary attachment information',
    'processors': [
        {
            'attachment': {
                'field': 'text',
                'target_field': 'extracted_text',
                'indexed_chars': indexed_chars,
                'ignore_missing': True,
            },
        },
        {
            'attachment': {
                'field': 'file',
                'target_field': 'extracted_file',
                'indexed_chars': indexed_chars,
                'ignore_missing': True,
            },
        },
        {
            'attachment': {
                'field': 'image',
                'target_field': 'extracted_image',
                'indexed_chars': indexed_chars,
                'ignore_missing': True,
            },
        },
        {
            'remove': {
                'field': 'file',
            },
        },
        {
            'remove': {
                'field': 'text',
            },
        },
        {
            'remove': {
                'field': 'image',
            },
        },
    ],
}


@implementer(IElasticSearchIndexQueueProcessor)
class ElasticSearchIndexQueueProcessor(object):
    """ a queue processor for ElasticSearch"""

    @property
    def _es_pipeline_name(self):
        return 'attachment_ingest_{0}'.format(index_name())

    def _create_index(seld, es):
        es.indices.create(index=index_name())
        self._setup_mapping(es)

    @ram.cache(lambda *args: index_name())
    def _check_for_ingest_pipeline(self, es):
        # do we have the ingest pipeline?
        try:
            es.ingest.get_pipeline(self._es_pipeline_name)
        except NotFoundError:
            es.ingest.put_pipeline(self._es_pipeline_name, INGEST_PIPELINES)

    def _check_for_mapping(self, es):
        if not self._get_mapping(es):
            raise ValueError('Can not fetch mapping.')

    def _get_mapping(self, es):
        request = getRequest()
        mapping = getattr(request, CACHE_ATTRIBUTE, None)
        if mapping is not None:
            return mapping
        try:
            mapping = es.indices.get_mapping(index=index_name())
        except TransportError as e:
            if e.status_code == 404:
                self._create_index(es)
                mapping = es.indices.get_mapping(index=index_name())
            else:
                raise
        setattr(request, CACHE_ATTRIBUTE, mapping)
        return mapping

    def _setup_mapping(self, es):
        es.indices.put_mapping(
            doc_type='content',
            index=index_name(),
            body=INITIAL_MAPPING,
        )
        request = getRequest()
        setattr(request, CACHE_ATTRIBUTE, None)

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
            doc_type='content',  # why do we still need it in ES6+?
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
            if 'attachment' not in record:
                continue
            yield record['attachment']['field']

    def _expand_binary_data(self, obj, data):
        max_size = es_config.max_blobsize
        for fieldname in self._iterate_binary_fields(obj, data):
            if fieldname not in data:
                data[fieldname] = None
                continue
            field = getattr(obj, fieldname, None)
            if field is None:
                data[fieldname] = None
                continue
            data[fieldname + '_meta'] = data[fieldname]
            if IBlobby.providedBy(field):
                with field.open() as fh:
                    data[fieldname] = base64.b64encode(fh.read())
            elif IRichTextValue.providedBy(field):
                data[fieldname] = base64.b64encode(
                    data[fieldname + '_meta']['data'].encode('utf8'),
                )
            if max_size and len(data[fieldname]) > max_size:
                data[fieldname] = None
                del data[fieldname + '_meta']
                logger.info(
                    'File too big for ElasticSearch Indexing: {0}'.format(
                        obj.absolute_url(),
                    ),
                )

    def _expand_rid(self, obj, data):
        cat = api.portal.get_tool('portal_catalog')
        path = '/'.join(obj.getPhysicalPath())
        data['rid'] = cat.getrid(path)

    def index(self, obj, attributes=None):
        query_blocker.block()
        es = get_ingest_client()
        if es is None:
            logger.warning(
                'No ElasticSearch client available.',
            )
            query_blocker.unblock()
            return
        try:
            self._check_for_ingest_pipeline(es)
            self._check_for_mapping(es)  # will also create the index
        except TransportError:
            logger.exception(
                'ElasticSearch connection failed for {0}'.format(
                    obj.absolute_url(),
                ),
            )
            query_blocker.unblock()
            return
        try:
            serializer = getMultiAdapter((obj, getRequest()), ISerializeToJson)
        except ComponentLookupError:
            logger.exception(
                'Abort ElasticSearch Indexing for {0}'.format(
                    obj.absolute_url(),
                ),
            )
            query_blocker.unblock()
            return
        try:
            data = serializer()
        except ComponentLookupError:
            logger.exception(
                'Abort ElasticSearch Indexing for {0}'.format(
                    obj.absolute_url(),
                ),
            )
            query_blocker.unblock()
            return
        self._reduce_data(data)
        self._expand_rid(obj, data)
        self._expand_binary_data(obj, data)
        uid = api.content.get_uuid(obj)
        es_kwargs = dict(
            index=index_name(),
            doc_type='content',
            id=uid,
            pipeline=self._es_pipeline_name,
            body=data,
            request_timeout=es_config.request_timeout,
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
        if es_config.use_celery:
            index_content.delay(obj.absolute_url(), es_kwargs)
        else:
            try:
                es.index(**es_kwargs)
            except Exception:
                logger.exception(
                    'indexing of {0} failed.'.format(
                        uid,
                    ),
                )
                import Globals
                if Globals.DevelopmentMode:
                    logger.debug(pformat(es_kwargs, indent=2))
        query_blocker.unblock()

    def reindex(self, obj, attributes=None, update_metadata=1):
        self.index(obj, attributes)

    def unindex(self, obj):
        index = index_name()
        if index is None:
            # portal no longer there
            return
        uid = api.content.get_uuid(obj)
        if es_config.use_celery:
            unindex_content.delay(
                index=index,
                doc_type='content',
                uid=uid,
                timeout=es_config.request_timeout,
            )
        else:
            es = get_ingest_client()
            if es is None:
                logger.warning(
                    'No ElasticSearch client available.',
                )
                return
            try:
                es.delete(
                    index=index,
                    doc_type='content',
                    id=uid,
                    request_timeout=es_config.request_timeout,
                )
            except Exception:
                logger.exception('unindexing of {0} failed'.format(uid))

    def begin(self):
        pass

    def commit(self, wait=None):
        pass

    def abort(self):
        pass

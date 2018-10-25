# -*- coding: utf-8 -*-
from collective.es.index.interfaces import IElasticSearchClient
from elasticsearch import Elasticsearch
from zope.component import provideUtility
from zope.interface import directlyProvides


class ElasticSearchIngressConfFactory(object):

    def __init__(self, section):
        self.section = section

    def _client_dict(self, value):
        if not value:
            value = [('127.0.0.1', '9200')]
        return [dict(zip(['host', 'port'], el)) for el in value]

    def prepare(self, *args, **kwargs):
        self.query = self._client_dict(self.section.query)
        self.ingest = self._client_dict(self.section.ingest)
        self.ssl = self.section.ssl
        self.verify_certs = self.section.verify_certs
        self.ca_certs = self.section.ca_certs
        self.client_cert = self.section.client_cert
        self.client_key = self.section.client_key
        self.request_timeout = self.section.request_timeout
        self.max_blobsize = self.section.max_blobsize
        self.use_celery = self.section.use_celery
        self.indexed_chars = self.section.indexed_chars
        self.search_fields = self.section.search_fields
        self.facets = self.section.facets

    def create(self):
        base_client = Elasticsearch(
            self.query,
            use_ssl=self.ssl,
            # here some more params need to be configured.
        )
        ingest_client = Elasticsearch(
            self.ingest,
            use_ssl=self.ssl,
            # here some more params need to be configured.
        )
        base_client.ingest = ingest_client
        base_client.zope_configuration = self.section
        directlyProvides(base_client, IElasticSearchClient)
        provideUtility(base_client)

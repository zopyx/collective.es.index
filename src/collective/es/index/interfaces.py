# -*- coding: utf-8 -*-
"""Module where all interfaces, events and exceptions live."""
from Products.CMFCore.interfaces import IIndexQueueProcessor
from zope.interface import Attribute
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class ICollectiveEsIndexLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""


class IElasticSearchIndexQueueProcessor(IIndexQueueProcessor):
    """An index queue processor for elasticsearch."""


class IElasticSearchClientProvider(Interface):
    """provides ingress and query clients"""

    query = Attribute('ElasticSearch client used for queries (ro)')

    ingest = Attribute(
        'ElasticSearch client used for add/update/deletes (rw). '
        'This includes ingest of binary data using a suitable converter. '
        'https://www.elastic.co/guide/en/elasticsearch/plugins/master/ingest-attachment.html'  # noqa
    )

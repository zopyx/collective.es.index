# -*- coding: utf-8 -*-
"""Module where all interfaces, events and exceptions live."""
from Products.CMFCore.interfaces import IIndexQueueProcessor
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer


class ICollectiveEsIndexLayer(IDefaultBrowserLayer):
    """Marker interface that defines a browser layer."""
    # unused, keep for BBB or future use


class IElasticSearchIndexQueueProcessor(IIndexQueueProcessor):
    """An index queue processor for elasticsearch."""


class IElasticSearchClient(Interface):
    """an initializd  python ElasticSearch object"""

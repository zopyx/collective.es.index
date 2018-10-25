# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.es.index.testing import COLLECTIVE_ES_INDEX_INTEGRATION_TESTING
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME

import time
import unittest


class TestESProxyIndexBasics(unittest.TestCase):
    """Test that proxy index works properly."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for following tests."""
        self.catalog = self.layer['portal']['portal_catalog']
        # install index
        from collective.es.index.esproxyindex import ElasticSearchProxyIndex
        espi = ElasticSearchProxyIndex(
            'espi',
            caller=self.catalog,
        )
        self.catalog.addIndex('espi', espi)

    def test_index_installed(self):
        """Test if proxy index is installed."""
        self.assertIn('espi', self.catalog.indexes())

    def test_get_query_client(self):
        """Test if client is found vi utility."""
        from collective.es.index.interfaces import IElasticSearchClient
        from collective.es.index.utils import get_query_client
        client = get_query_client()
        assert(IElasticSearchClient.providedBy(client))


class TestESProxyIndexAllQuery(unittest.TestCase):
    """Test that proxy index works properly."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for following tests."""
        self.catalog = self.layer['portal']['portal_catalog']
        from collective.es.index.esproxyindex import ElasticSearchProxyIndex
        from collective.es.index.utils import get_query_client
        client = get_query_client()
        client.indices.create('testing_plone')
        espi = ElasticSearchProxyIndex(
            'espi',
            caller=self.catalog,
        )
        self.catalog.addIndex('espi', espi)
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)
        portal.invokeFactory('Document', 'd1', title='Test one')
        portal.invokeFactory('Document', 'd2', title='Test two')
        portal.invokeFactory('Document', 'd3', title='Test three')
        # give es time to index documents
        time.sleep(2)

    def tearDown(self):
        from collective.es.index.utils import remove_index
        remove_index('testing_plone')

    def test_query(self):
        idx = self.catalog._catalog.indexes['espi']
        result = idx._apply_index({'espi': {'query': 'Test'}})
        self.assertGreater(len(result[0]), 2)


class TestESProxyIndexFulltext(unittest.TestCase):
    """Test that proxy index works properly."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for following tests."""
        self.catalog = self.layer['portal']['portal_catalog']
        # install index
        from collective.es.index.esproxyindex import ElasticSearchProxyIndex
        from plone.app.textfield.value import RichTextValue
        from collective.es.index.utils import get_query_client
        client = get_query_client()
        client.indices.create('testing_plone')
        espi = ElasticSearchProxyIndex(
            'espi',
            caller=self.catalog,
        )
        self.catalog.addIndex('espi', espi)
        portal = self.layer['portal']
        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)
        portal.invokeFactory('Document', 'd1', title='Test one')
        portal.d1.text = RichTextValue('Blah Blah Blah',
                                       'text/plain',
                                       'text/html')
        portal.invokeFactory('Document', 'd2', title='Test two')
        portal.d2.text = RichTextValue('Yada Yada Yada',
                                       'text/plain',
                                       'text/html')
        portal.invokeFactory('Document', 'd3', title='Test three')
        portal.d3.text = RichTextValue('Something completely different',
                                       'text/plain',
                                       'text/html')
        # give es time to index documents
        time.sleep(2)

    def tearDown(self):
        from collective.es.index.utils import remove_index
        remove_index('testing_plone')

    def test_query_empty_result(self):
        idx = self.catalog._catalog.indexes['espi']
        result = idx._apply_index({'espi': {'query': 'foo'}})
        self.assertEqual(len(result[0]), 0)

    def test_query_plone(self):
        idx = self.catalog._catalog.indexes['espi']
        result = idx._apply_index({'espi': {'query': 'yada'}})
        self.assertEqual(len(result[0]), 1)

# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.es.index.testing import COLLECTIVE_ES_INDEX_INTEGRATION_TESTING
from plone import api

import unittest


TEST_TEMPLATE = """
{}
"""


class TestESProxyIndex(unittest.TestCase):
    """Test that proxy index works properly."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for following tests."""
        self.portal = self.layer['portal']
        # install index
        from collective.es.index.esproxyindex import ElasticSearchProxyIndex
        espi = ElasticSearchProxyIndex(
            'espi',
            extra={
                'query_template': TEST_TEMPLATE,
            },
            caller=self.portal.portal_catalog,
        )
        self.portal.portal_catalog.addIndex('espi', espi)

    def test_index_installed(self):
        """Test if proxy index is installed."""
        self.assertIn(
            'espi',
            [x.getId() for x in self.portal.portal_catalog.getIndexObjects()],
        )

    def test_query_index(self):
        pass

# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.es.index.testing import COLLECTIVE_ES_INDEX_INTEGRATION_TESTING
from plone import api

import unittest


TEST_TEMPLATE_SIMPLE = """\
{
    "foo": "{{bar}}"
}
"""


class TestESProxyIndex(unittest.TestCase):
    """Test that proxy index works properly."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for following tests."""
        self.catalog = self.layer['portal']['portal_catalog']
        # install index
        from collective.es.index.esproxyindex import ElasticSearchProxyIndex
        espi = ElasticSearchProxyIndex(
            'espi',
            extra={
                'query_template': TEST_TEMPLATE_SIMPLE,
            },
            caller=self.catalog,
        )
        self.catalog.addIndex('espi', espi)

    def test_index_installed(self):
        """Test if proxy index is installed."""
        self.assertIn('espi', self.catalog.indexes())

    def test_template(self):
        idx = self.catalog._catalog.indexes['espi']
        result = idx._apply_template({'bar': 'baz'})
        self.assertEqual(result['foo'], u'baz')

#    def test_query(self):
#        idx = self.catalog._catalog.indexes['espi']

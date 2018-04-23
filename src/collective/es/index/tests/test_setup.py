# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.es.index.testing import COLLECTIVE_ES_INDEX_INTEGRATION_TESTING
from plone import api
from plone.app.testing import applyProfile

import unittest


class TestSetup(unittest.TestCase):
    """Test that collective.es.index is properly installed."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        applyProfile(self.portal, 'collective.es.index:default')

    def test_product_installed(self):
        """Test if collective.es.index is installed."""
        self.assertTrue(
            self.installer.isProductInstalled('collective.es.index')
        )
        st_index = self.portal.portal_catalog._catalog.getIndex(
            'SearchableText'
        )
        self.assertEqual(st_index.meta_type, 'ElasticSearchProxyIndex')


class TestUninstall(unittest.TestCase):

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        applyProfile(self.portal, 'collective.es.index:default')
        self.installer.uninstallProducts(['collective.es.index'])

    def test_product_uninstalled(self):
        """Test if collective.es.index is cleanly uninstalled."""
        self.assertFalse(
            self.installer.isProductInstalled('collective.es.index'),
        )
        st_index = self.portal.portal_catalog._catalog.getIndex(
            'SearchableText'
        )
        self.assertEqual(st_index.meta_type, 'ZCTextIndex')

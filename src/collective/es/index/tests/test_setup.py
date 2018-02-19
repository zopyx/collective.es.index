# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.es.index.testing import COLLECTIVE_ES_INDEX_INTEGRATION_TESTING  # noqa
from plone import api

import unittest


class TestSetup(unittest.TestCase):
    """Test that collective.es.index is properly installed."""

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if collective.es.index is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'collective.es.index'))

    def test_browserlayer(self):
        """Test that ICollectiveEsIndexLayer is registered."""
        from collective.es.index.interfaces import (
            ICollectiveEsIndexLayer)
        from plone.browserlayer import utils
        self.assertIn(
            ICollectiveEsIndexLayer,
            utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = COLLECTIVE_ES_INDEX_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['collective.es.index'])

    def test_product_uninstalled(self):
        """Test if collective.es.index is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'collective.es.index'))

    def test_browserlayer_removed(self):
        """Test that ICollectiveEsIndexLayer is removed."""
        from collective.es.index.interfaces import \
            ICollectiveEsIndexLayer
        from plone.browserlayer import utils
        self.assertNotIn(
           ICollectiveEsIndexLayer,
           utils.registered_layers())

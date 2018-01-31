# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

import collective.es.index


class CollectiveEsIndexLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        self.loadZCML(package=collective.es.index)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'collective.es.index:default')


COLLECTIVE_ES_INDEX_FIXTURE = CollectiveEsIndexLayer()


COLLECTIVE_ES_INDEX_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_ES_INDEX_FIXTURE,),
    name='CollectiveEsIndexLayer:IntegrationTesting'
)


COLLECTIVE_ES_INDEX_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(COLLECTIVE_ES_INDEX_FIXTURE,),
    name='CollectiveEsIndexLayer:FunctionalTesting'
)


COLLECTIVE_ES_INDEX_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        COLLECTIVE_ES_INDEX_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='CollectiveEsIndexLayer:AcceptanceTesting'
)

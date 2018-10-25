# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2

class ProductConfiguration(object):
    max_blobsize = 0
    request_timeout = 20
    use_celery = False
configuration = ProductConfiguration()

import collective.es.index.utils
collective.es.index.utils.index_name = lambda: 'testing_plone'
collective.es.index.utils.get_configuration = lambda: configuration


class CollectiveEsIndexLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.restapi
        import collective.es.index
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=collective.es.index)
        z2.installProduct(app, 'collective.es.index')

    def setUpPloneSite(self, portal):
        # provide an ES connection
        from collective.es.index.interfaces import IElasticSearchClient
        from elasticsearch import Elasticsearch
        from zope.component import provideUtility
        from zope.interface import directlyProvides
        es = Elasticsearch(
            [{'host': '127.0.0.1', 'port': '9200'}],
            use_ssl=False,
        )
        ingest = Elasticsearch(
            [{'host': '127.0.0.1', 'port': '9200'}],
            use_ssl=False,
        )
        es.zope_configuration = configuration
        es.ingest = ingest
        directlyProvides(es, IElasticSearchClient)
        provideUtility(es)


COLLECTIVE_ES_INDEX_FIXTURE = CollectiveEsIndexLayer()


COLLECTIVE_ES_INDEX_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_ES_INDEX_FIXTURE,),
    name='CollectiveEsIndexLayer:IntegrationTesting',
)


COLLECTIVE_ES_INDEX_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(COLLECTIVE_ES_INDEX_FIXTURE,),
    name='CollectiveEsIndexLayer:FunctionalTesting',
)


COLLECTIVE_ES_INDEX_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        COLLECTIVE_ES_INDEX_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name='CollectiveEsIndexLayer:AcceptanceTesting',
)

# -*- coding: utf-8 -*-
"""Init and utils."""
from zope.i18nmessageid import MessageFactory


TESTING = False


_ = MessageFactory('collective.es.index')


def initialize(context):
    from . import esproxyindex
    context.registerClass(
        esproxyindex.ElasticSearchProxyIndex,
        permission='Add Pluggable Index',
        constructors=(
            esproxyindex.manage_addESPIndexForm,
            esproxyindex.manage_addESPIndex,
        ),
        icon='www/index.gif',
        visibility=None,
    )

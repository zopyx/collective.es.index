# -*- coding: utf-8 -*-
"""Init and utils."""
from zope.i18nmessageid import MessageFactory


_ = MessageFactory('collective.es.index')


def initialize(context):
    from . import searchabletextindex
    context.registerClass(
        searchabletextindex.ESSearchableTextIndex,
        permission='Add Pluggable Index',
        constructors=(
            searchabletextindex.manage_addESSTIndexForm,
            searchabletextindex.manage_addESSTIndex,
        ),
        icon='www/index.gif',
        visibility=None,
    )

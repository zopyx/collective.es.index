# -*- coding: utf-8 -*-
"""Installer for the collective.es.index package."""
from setuptools import setup


setup(
    # zest releaser does not change cfg file.
    version='1.0a1',

    # thanks to this bug
    # https://github.com/pypa/setuptools/issues/1136
    # we need one line in here:
    package_dir={'': 'src'},
)

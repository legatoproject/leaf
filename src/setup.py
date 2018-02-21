#!/usr/bin/env python3

from leaf import __version__
from setuptools import setup


setup(name='leaf',
      version=__version__,
      packages=['leaf'],
      entry_points={
          'console_scripts': [
              'leaf = leaf.cli:run'
          ]
      },
      test_suite='nose.collector',
      tests_require=['nose'],
      )

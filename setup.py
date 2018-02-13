#!/usr/bin/env python3

from setuptools import setup
from leaf import __version__

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

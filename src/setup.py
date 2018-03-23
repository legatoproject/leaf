#!/usr/bin/env python3

from leaf import __version__
from setuptools import setup


setup(name='leaf',
      version=__version__,
      packages=[
          'leaf'
      ],
      entry_points={
          'console_scripts': [
              'leafpm = leaf.cli_packagemanager:main',
              'leaf = leaf.cli_profile:main'
          ]
      },
      test_suite='nose.collector',
      tests_require=['nose'],
      )

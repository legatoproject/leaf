#!/usr/bin/env python3

from leaf import __version__
from setuptools import setup


setup(name='leaf',
      version=__version__,
      packages=[
          'leaf',
          'leaf.model',
          'leaf.core',
          'leaf.cli'
      ],
      entry_points={
          'console_scripts': [
              'leaf = leaf.cli.cli:main'
          ]
      },
      test_suite='nose.collector',
      tests_require=['nose'],
      )

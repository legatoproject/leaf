#!/usr/bin/env python3

from pathlib import Path
from setuptools import setup

from leaf import __version__

SETUP_FOLDER = Path(__file__).parent
MANPAGE_FOLDER = SETUP_FOLDER / 'man' / 'man1'
print (MANPAGE_FOLDER.resolve())
EXTENSIONS_FOLDER = SETUP_FOLDER / 'extensions'
assert MANPAGE_FOLDER.exists()
assert EXTENSIONS_FOLDER.exists()

setup(name='leaf',
      version=__version__,
      packages=[
          'leaf',
          'leaf.model',
          'leaf.core',
          'leaf.cli'
      ],
      data_files=[
          ('man/man1', [str(x.relative_to(SETUP_FOLDER))
                        for x in MANPAGE_FOLDER.iterdir()
                        if x.is_file() and x.name.startswith("leaf")]),
          ('bin', [str(x.relative_to(SETUP_FOLDER))
                   for x in EXTENSIONS_FOLDER.iterdir()
                   if x.is_file() and x.name.startswith("leaf-")])
      ],
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'leaf = leaf.cli.cli:main'
          ]
      },
      test_suite='nose.collector',
      tests_require=['nose'],
      )

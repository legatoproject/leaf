#!/usr/bin/env python3

from pathlib import Path
from setuptools import setup


ROOT_FOLDER = Path(__file__).parent
RESOURCES_FOLDER = ROOT_FOLDER / 'resources'
MANPAGE_FOLDER = RESOURCES_FOLDER / 'man' / 'man1'


def findResourcesFiles():
    if not RESOURCES_FOLDER.exists():
        raise ValueError("Cannot find resources folder")
    if not MANPAGE_FOLDER.exists():
        raise ValueError("Manpages have not been generated yet")

    resMap = {}

    def visit(folder):
        key = str(folder.relative_to(RESOURCES_FOLDER))
        for item in folder.iterdir():
            if item.is_dir():
                visit(item)
            else:
                if key not in resMap:
                    resMap[key] = []
                value = str(item.relative_to(ROOT_FOLDER))
                resMap[key].append(value)
    visit(RESOURCES_FOLDER)
    out = []
    for k, v in resMap.items():
        out.append((k, v))
        print("Found resources in %s: %s" % (k, ", ".join(v)))
    return out


setup(name='leaf',
      license='Mozilla Public License 2.0',
      description='Leaf is a package and workspace manager',
      use_scm_version={
          'version_scheme': 'post-release'
      },
      setup_requires=['setuptools_scm'],
      package_dir={'': 'src'},
      packages=[
          'leaf',
          'leaf.cli',
          'leaf.core',
          'leaf.format',
          'leaf.model'
      ],
      entry_points={
          'console_scripts': [
              'leaf = leaf.__main__:main'
          ]
      },
      data_files=findResourcesFiles(),
      include_package_data=True,
      test_suite='nose.collector',
      tests_require=['nose', 'coverage'])

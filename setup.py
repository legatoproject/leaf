#!/usr/bin/env python3

from pathlib import Path
from setuptools import setup


ROOT_FOLDER = Path(__file__).parent
RESOURCES_FOLDER = ROOT_FOLDER / "resources"
MANPAGE_FOLDER = RESOURCES_FOLDER / "man" / "man1"


def _find_resources():
    if not RESOURCES_FOLDER.exists():
        raise ValueError("Cannot find resources folder")
    if not MANPAGE_FOLDER.exists():
        raise ValueError("Manpages have not been generated yet")

    resources_map = {}

    def visit(folder):
        key = str(folder.relative_to(RESOURCES_FOLDER))
        for item in folder.iterdir():
            if item.is_dir():
                visit(item)
            else:
                if key not in resources_map:
                    resources_map[key] = []
                value = str(item.relative_to(ROOT_FOLDER))
                resources_map[key].append(value)

    visit(RESOURCES_FOLDER)
    out = []
    for folder, items in resources_map.items():
        out.append((folder, items))
        print("    Resources in {}".format(folder))
        for item in items:
            print("        {}".format(item))
    return out


setup(
    name="leaf",
    license="Mozilla Public License 2.0",
    description="Leaf is a package and workspace manager",
    use_scm_version={"version_scheme": "post-release"},
    setup_requires=["setuptools_scm"],
    package_dir={"": "src"},
    packages=["leaf", "leaf.core", "leaf.model", "leaf.rendering", "leaf.rendering.renderer", "leaf.api", "leaf.cli", "leaf.cli.commands"],
    entry_points={"console_scripts": ["leaf = leaf.__main__:main"]},
    data_files=_find_resources(),
    include_package_data=True,
)

"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import argparse

from leaf.api import PackageManager
from leaf.cli.base import LeafCommand
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import IDENTIFIER_GETTER
from leaf.model.tags import TagUtils
from leaf.rendering.renderer.manifest import ManifestListRenderer


class SearchCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "search", "search for available packages")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-a", "--all", dest="only_master_packages", action="store_false", help="display all packages, not only master packages")
        parser.add_argument("-t", "--tag", dest="tags", action="append", metavar="TAG", help="filter search results matching with given tag")
        parser.add_argument("keywords", metavar="KEYWORD", nargs=argparse.ZERO_OR_MORE)

    def execute(self, args, uargs):
        pm = PackageManager()

        metafilter = MetaPackageFilter()
        if args.only_master_packages:
            metafilter.only_master_packages()

        if args.tags is not None:
            for t in args.tags:
                metafilter.with_tag(t)

        if args.keywords is not None and len(args.keywords) > 0:
            for kw in args.keywords:
                metafilter.with_keyword(kw)

        # Pkg list
        mflist = sorted(pm.list_available_packages().values(), key=IDENTIFIER_GETTER)
        # manage tags
        TagUtils.tag_latest(mflist)
        TagUtils.tag_installed(mflist, pm.list_installed_packages().keys())

        # Print filtered packages
        rend = ManifestListRenderer(metafilter)
        rend.extend(filter(metafilter.matches, mflist))
        pm.print_renderer(rend)

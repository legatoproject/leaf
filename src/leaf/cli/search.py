'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from leaf.cli.cliutils import LeafCommand
from leaf.core.tags import TagManager
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import Manifest
from leaf.format.searchrenderer import SearchRenderer


class SearchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            "search",
            "search for available packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument("-a", "--all",
                            dest="allPackages",
                            action="store_true",
                            help="display all packages, not only master packages")
        parser.add_argument("-t", "--tag",
                            dest="tags",
                            action="append",
                            metavar="TAG",
                            help="filter search results matching with given tag")
        parser.add_argument('keywords', metavar="KEYWORD",
                            nargs=argparse.ZERO_OR_MORE)

    def execute(self, args):
        logger = self.getLogger(args)
        pm = self.getPackageManager(args)

        pkgFilter = MetaPackageFilter()
        if not args.allPackages:
            pkgFilter.onlyMasterPackages()

        if args.tags is not None:
            for t in args.tags:
                pkgFilter.withTag(t)

        if args.keywords is not None and len(args.keywords) > 0:
            for kw in args.keywords:
                pkgFilter.withKeyword(kw)

        # Pkg list
        mfList = sorted(pm.listAvailablePackages().values(),
                        key=Manifest.getIdentifier)
        # manage tags
        TagManager().tagLatest(mfList)
        TagManager().tagInstalled(mfList, pm.listInstalledPackages().keys())

        # Print filtered packages
        rend = SearchRenderer(pkgFilter)
        rend.extend(mf for mf in mfList if pkgFilter.matches(mf))
        logger.printRenderer(rend)

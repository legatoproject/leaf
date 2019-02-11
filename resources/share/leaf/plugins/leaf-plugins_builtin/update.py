#!/usr/bin/env python3
# LEAF_DESCRIPTION update current profile packages
'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''


from leaf.cli.plugins import LeafPluginCommand
from leaf.model.modelutils import groupPackageIdentifiersByName
from leaf.core.error import InvalidPackageNameException
from leaf.model.package import PackageIdentifier


def getLatestAvailablePackage(motif, piList):
    if PackageIdentifier.isValidIdentifier(motif):
        pi = PackageIdentifier.fromString(motif)
        return pi if pi in piList else None
    out = None
    for pi in piList:
        if pi.name == motif:
            if out is None or pi > out:
                out = pi
    return out


class UpdagePlugin(LeafPluginCommand):

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('-p', '--add-package',
                            dest='packages',
                            action='append',
                            metavar='PKG_NAME',
                            help="specific packages to update")

    def execute(self, args, uargs):
        workspaceManager = self.getWorkspaceManager()
        logger = workspaceManager.logger

        profileName = workspaceManager.getCurrentProfileName()
        profile = workspaceManager.getProfile(profileName)

        profilePackageMap = profile.getPackagesMap()
        groupedPackagesMap = groupPackageIdentifiersByName(
            workspaceManager.listInstalledPackages())
        groupedPackagesMap = groupPackageIdentifiersByName(
            workspaceManager.listAvailablePackages(),
            pkgMap=groupedPackagesMap)

        updatePiList = []

        motifList = args.packages if args.packages is not None else profilePackageMap.keys()
        for motif in motifList:
            pi = None
            if PackageIdentifier.isValidIdentifier(motif):
                # User force specific version
                pi = PackageIdentifier.fromString(motif)
                if pi.name not in groupedPackagesMap or pi not in groupedPackagesMap[pi.name]:
                    # Unknwon package
                    pi = None
            elif motif in groupedPackagesMap:
                # Get latest version
                pi = groupedPackagesMap[motif][-1]

            if pi is None:
                # Unknown package identifier
                raise InvalidPackageNameException(motif)

            if pi is not None and pi not in updatePiList:
                # Get PI in profile
                previousPi = profilePackageMap.get(pi.name)
                if previousPi is None:
                    # Package not in profile yet, add it
                    if workspaceManager.confirm("Do you want to add package %s?" % pi):
                        updatePiList.append(pi)
                elif previousPi != pi:
                    # Package already in profile with a different version, update it
                    if workspaceManager.confirm("Do you want to update package %s from %s to %s?" % (pi.name,
                                                                                                     previousPi.version,
                                                                                                     pi.version)):
                        updatePiList.append(pi)
                else:
                    # Package already in profile with same version, do nothing
                    pass

        if len(updatePiList) == 0:
            logger.printDefault("Nothing to do")
        else:
            profile.addPackages(updatePiList)
            workspaceManager.updateProfile(profile)
            workspaceManager.provisionProfile(profile)

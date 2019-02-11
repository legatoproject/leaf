'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from leaf.model.modelutils import findLatestVersion, findManifest
from leaf.model.package import Manifest, PackageIdentifier


class DependencyUtils():
    '''
    Used to build the dependency tree using dynamic conditions
    '''

    @staticmethod
    def __buildTree(piList, mfMap, out,
                    env=None,
                    onlyKeepLatest=False,
                    ignoredPiList=None,
                    ignoreUnknown=False):
        '''
        Build a manifest list of given PackageIdentifiers and its dependecies
        @return: Manifest list
        '''
        if ignoredPiList is None:
            ignoredPiList = []
        for pi in piList:
            if pi not in ignoredPiList:
                ignoredPiList.append(pi)
                mf = findManifest(pi, mfMap,
                                  ignoreUnknown=ignoreUnknown)
                if mf is not None and mf not in out:
                    # Begin by adding dependencies
                    DependencyUtils.__buildTree(mf.getLeafDependsFromEnv(env),
                                                mfMap,
                                                out,
                                                env=env,
                                                ignoredPiList=ignoredPiList,
                                                ignoreUnknown=ignoreUnknown)
                    out.append(mf)

        if onlyKeepLatest:
            # Create a MF dict overriding package to latest version previously computed
            altMfMap = {}
            for pi in mfMap:
                latestMf = None
                for mf in out:
                    if pi.name == mf.getIdentifier().name:
                        if latestMf is None or mf.getIdentifier() > latestMf.getIdentifier():
                            latestMf = mf
                altMfMap[pi] = latestMf or mfMap[pi]
            # Reset out
            del out[:]
            # Reinvoke and give latest versions,
            # NB reset ignoredPiList to restart algo
            DependencyUtils.__buildTree(piList,
                                        altMfMap,
                                        out,
                                        env=env,
                                        ignoreUnknown=ignoreUnknown)

    @staticmethod
    def installed(piList, ipMap,
                  env=None,
                  onlyKeepLatest=False,
                  ignoreUnknown=False):
        '''
        Build a dependency list of installed packages and dependencies.
        Returns a list of InstalledPackage
        '''
        out = []
        DependencyUtils.__buildTree(piList, ipMap, out,
                                    env=env,
                                    onlyKeepLatest=onlyKeepLatest,
                                    ignoreUnknown=ignoreUnknown)
        return out

    @staticmethod
    def install(piList, apMap, ipMap,
                env=None):
        '''
        Build the list of packages to install, with needed dependencies.
        Already installed packages are removed for the list.
        Packages are sorted for install order.
        Returns a list of AvailablePackage
        '''
        out = []

        # Build a map containing all knwon packages
        allKnownPackages = dict(apMap)
        allKnownPackages.update(ipMap)

        # Build the list from available packages
        DependencyUtils.__buildTree(piList, allKnownPackages, out,
                                    env=env)
        # Remove already installed packages
        out = [ap for ap in out if ap.getIdentifier() not in ipMap]
        return out

    @staticmethod
    def uninstall(piList, ipMap,
                  env=None):
        '''
        Build the list of packages to uninstall.
        Dependencies are preserved (ie dependencies needed by other installed packages are kept)
        Packages are sorted for uninstall order.
        Returns a list of InstalledPackage
        '''
        out = []
        # Build the list from installed packages
        DependencyUtils.__buildTree(piList, ipMap, out,
                                    env=env,
                                    ignoreUnknown=True)
        # for uninstall, reverse order
        out = list(reversed(out))
        # Maintain dependencies
        otherPiList = [ip.getIdentifier()
                       for ip in ipMap.values()
                       if ip not in out]
        # Keep all configurations (ie env=None) for all other installed packages
        for neededIp in DependencyUtils.installed(otherPiList, ipMap,
                                                  env=None,
                                                  ignoreUnknown=True):
            if neededIp in out:
                out.remove(neededIp)
        return out

    @staticmethod
    def prereq(piList, apMap, ipMap,
               env=None):
        '''
        Return the list of prereq packages to install
        Packages are sorted in alpha order.
        Returns a list of AvailablePackages
        '''
        out = []
        # First get the install tree
        apList = DependencyUtils.install(piList, apMap, ipMap,
                                         env=env)
        # Get all prereq PI and find corresponding AP
        for ap in apList:
            for pis in ap.getLeafRequires():
                pi = PackageIdentifier.fromString(pis)
                ap = findManifest(pi, apMap)
                out.append(ap)
        # sort alphabetically and ensure no dupplicates
        out = list(sorted(set(out), key=Manifest.getIdentifier))
        return out

    @staticmethod
    def upgrade(piNameList, apMap, ipMap,
                env=None):
        '''
        Return a tuple of 2 lists:
         - First contains the AvailablePackages  to install for an upgrade
         - Second contains InstalledPackages that can be uninstalled
        uninstalled after
        '''

        # Update all auto upgradable packages if no input given
        if piNameList is None:
            piNameList = set([pi.name for pi,
                              ip in ipMap.items() if ip.isAutoUpgrade()])

        # Compute the list of package to install
        installList = []
        for piName in piNameList:
            latestInstalled = findLatestVersion(piName, ipMap)
            latestAvailable = findLatestVersion(piName, apMap,
                                                ignoreUnknown=False)
            if latestAvailable is not None and latestAvailable > latestInstalled:
                ap = apMap[latestAvailable]
                if ap not in installList:
                    installList.append(ap)

        # Compute the list of packages to uninstall
        uninstallList = []
        for ap in installList:
            piToBeInstalled = ap.getIdentifier()
            for installedPi, ip in ipMap.items():
                if installedPi.name == piToBeInstalled.name and piToBeInstalled > installedPi and ip.isAutoUpgrade():
                    uninstallList.append(ipMap[installedPi])
        uninstallList = sorted(uninstallList, key=Manifest.getIdentifier)
        return (installList, uninstallList)

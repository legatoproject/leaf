'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from enum import IntEnum, unique

from leaf.core.error import InvalidPackageNameException
from leaf.model.package import Manifest, PackageIdentifier


@unique
class DependencyType(IntEnum):
    INSTALLED = 1
    AVAILABLE = 2
    INSTALL = 3
    UNINSTALL = 4
    PREREQ = 5


@unique
class DependencyStrategy(IntEnum):
    ALL_VERSIONS = 0
    LATEST_VERSION = 1


class DependencyManager():
    '''
    Used to build the dependency tree using dynamic conditions
    '''

    @staticmethod
    def _find(pi, mfMap,
              latestVersions=None,
              ignoreUnknown=False):
        '''
        Return a Manifest given a PackageIdentifier
        '''
        if latestVersions is not None and pi.name in latestVersions:
            pi = latestVersions[pi.name]
        if pi not in mfMap and not ignoreUnknown:
            raise InvalidPackageNameException(pi)
        return mfMap.get(pi)

    @staticmethod
    def _getLatestVersions(piList):
        '''
        Build a dist of name/pi of the latest versions of given pi list
        '''
        out = {}
        for pi in piList:
            if pi.name not in out or out[pi.name] < pi:
                out[pi.name] = pi
        return out

    @staticmethod
    def _buildTree(piList,
                   mfMap,
                   out,
                   env=None,
                   strategy=DependencyStrategy.ALL_VERSIONS,
                   latestVersions=None,
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
                mf = DependencyManager._find(pi, mfMap,
                                             latestVersions=latestVersions,
                                             ignoreUnknown=ignoreUnknown)
                if mf is not None and mf not in out:
                    # Begin by adding dependencies
                    DependencyManager._buildTree(mf.getLeafDependsFromEnv(env),
                                                 mfMap,
                                                 out,
                                                 env=env,
                                                 strategy=strategy,
                                                 latestVersions=latestVersions,
                                                 ignoredPiList=ignoredPiList,
                                                 ignoreUnknown=ignoreUnknown)
                    out.append(mf)

        if strategy == DependencyStrategy.LATEST_VERSION and latestVersions is None:
            # Ignore all 'non-latest versions'
            latestVersions = DependencyManager._getLatestVersions(
                map(Manifest.getIdentifier, out))
            # Reset out
            del out[:]
            # Reinvoke and give latest versions,
            # NB reset ignoredPiList to restart algo
            DependencyManager._buildTree(piList,
                                         mfMap,
                                         out,
                                         env=env,
                                         strategy=strategy,
                                         latestVersions=latestVersions,
                                         ignoreUnknown=ignoreUnknown)

    @staticmethod
    def compute(piList,
                depType,
                strategy=DependencyStrategy.ALL_VERSIONS,
                apMap=None,
                ipMap=None,
                env=None,
                ignoreUnknown=False):
        out = []
        if depType == DependencyType.AVAILABLE:
            if apMap is None:
                raise ValueError()
            # In case of available, only build the list
            DependencyManager._buildTree(piList, apMap, out,
                                         env=env,
                                         strategy=strategy,
                                         ignoreUnknown=ignoreUnknown)
        elif depType == DependencyType.INSTALLED:
            if ipMap is None:
                raise ValueError()
            # In case of installed, only build the list
            DependencyManager._buildTree(piList, ipMap, out,
                                         env=env,
                                         strategy=strategy,
                                         ignoreUnknown=ignoreUnknown)
        elif depType == DependencyType.INSTALL:
            if ipMap is None or apMap is None:
                raise ValueError()
            # Build the list from available packages
            DependencyManager._buildTree(piList, apMap, out,
                                         env=env,
                                         strategy=strategy,
                                         ignoreUnknown=False)
            # Remove already installed packages
            out = [ap for ap in out if ap.getIdentifier() not in ipMap]
        elif depType == DependencyType.UNINSTALL:
            if ipMap is None:
                raise ValueError()
            # Build the list from available packages
            DependencyManager._buildTree(piList, ipMap, out,
                                         ignoreUnknown=True)
            # for uninstall, reverse order
            out = list(reversed(out))
            # Maintain dependencies
            for neededIp in DependencyManager.compute([ip.getIdentifier() for ip in ipMap.values() if ip not in out],
                                                      DependencyType.INSTALLED,
                                                      strategy=strategy,
                                                      ipMap=ipMap,
                                                      ignoreUnknown=True):
                if neededIp in out:
                    out.remove(neededIp)
        elif depType == DependencyType.PREREQ:
            # First get the install tree
            apList = DependencyManager.compute(piList,
                                               DependencyType.INSTALL,
                                               strategy=strategy,
                                               apMap=apMap,
                                               ipMap=ipMap,
                                               env=env)
            prereqPiList = set()
            # Get all prereq PI
            for ap in apList:
                prereqPiList.update(map(PackageIdentifier.fromString,
                                        ap.getLeafRequires()))
            # return a list of AP
            out = [DependencyManager._find(pi, apMap) for pi in prereqPiList]
            # sort alphabetically
            out = list(sorted(out, key=Manifest.getIdentifier))
        else:
            raise ValueError()
        return out

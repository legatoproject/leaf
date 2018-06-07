'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict

from leaf.model.package import Manifest


class TagManager():
    '''
    Class used to tag packages
    '''

    LATEST = 'latest'
    INSTALLED = 'installed'
    CURRENT = 'current'

    def tagLatest(self, mfList):
        '''
        Add the 'latest' tag to packages with the latest version
        '''
        mapByName = OrderedDict()
        for mf in mfList:
            pkgName = mf.getIdentifier().name
            if pkgName not in mapByName:
                mapByName[pkgName] = []
            mapByName[pkgName].append(mf)
        for pkgList in mapByName.values():
            latest = next(iter(sorted(pkgList,
                                      key=Manifest.getIdentifier,
                                      reverse=True)))
            latest.customTags.append(TagManager.LATEST)

    def tagInstalled(self, mfList, piList):
        '''
        Tag packages from given mfList as installed if they are in the given piList 
        '''
        for mf in mfList:
            if mf.getIdentifier() in piList:
                mf.customTags.append(TagManager.INSTALLED)

    def tagCurrent(self, mfList, pf):
        '''
        Tag packages in mfList as current if they are in the given profile
        '''
        for mf in mfList:
            if str(mf.getIdentifier()) in pf.getPackages():
                mf.customTags.append(TagManager.CURRENT)

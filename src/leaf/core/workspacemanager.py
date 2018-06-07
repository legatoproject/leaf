'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
import shutil

from leaf import __version__
from leaf.constants import LeafFiles, JsonConstants
from leaf.core.coreutils import packageListToEnvironnement
from leaf.core.dependencies import DependencyManager, DependencyType,\
    DependencyStrategy
from leaf.model.config import WorkspaceConfiguration
from leaf.model.package import Manifest, PackageIdentifier
from leaf.model.workspace import Profile
from leaf.utils import jsonLoadFile, checkSupportedLeaf, jsonWriteFile


class WorkspaceManager():
    '''
    Represent a workspace, where leaf profiles apply
    '''

    def __init__(self, rootFolder, app):
        self.app = app
        self.logger = app.logger
        self.rootFolder = rootFolder
        self.configFile = rootFolder / LeafFiles.WS_CONFIG_FILENAME
        self.dataFolder = rootFolder / LeafFiles.WS_DATA_FOLDERNAME
        self.currentLink = self.dataFolder / LeafFiles.CURRENT_PROFILE_LINKNAME

    def readConfiguration(self, initIfNeeded=False):
        '''
        Return the configuration and if current leaf version is supported
        '''
        if not self.configFile.exists() and initIfNeeded:
            self.writeConfiguration(WorkspaceConfiguration(OrderedDict()))
        wsc = WorkspaceConfiguration(jsonLoadFile(self.configFile))
        checkSupportedLeaf(wsc.jsonpath(JsonConstants.INFO_LEAF_MINVER),
                           exceptionMessage="Leaf has to be updated to work with this workspace")
        # Configure app with ws configuration
        self.app.updateUserConfiguration(remoteAddList=wsc.getRemotes())
        return wsc

    def writeConfiguration(self, wsc):
        '''
        Write the configuration and set the min leaf version to current version
        '''
        if not self.dataFolder.exists():
            self.dataFolder.mkdir()
        wsc.jsoninit(key=JsonConstants.WS_LEAFMINVERSION,
                     value=__version__,
                     force=True)
        tmpFile = self.dataFolder / ("tmp-" + LeafFiles.WS_CONFIG_FILENAME)
        jsonWriteFile(tmpFile, wsc.json, pp=True)
        tmpFile.rename(self.configFile)

    def updateWorkspaceConfiguration(self,
                                     envSetMap=None, envUnsetList=None,
                                     remoteAddList=None, remoteRmList=None):
        wsc = self.readConfiguration()
        wsc.updateEnv(envSetMap, envUnsetList)
        wsc.updateRemotes(remoteAddList, remoteRmList)
        self.writeConfiguration(wsc)

    def getAllProfiles(self, wsc=None):
        if wsc is None:
            wsc = self.readConfiguration()
        out = OrderedDict()
        for name, pfJson in wsc.getProfiles().items():
            out[name] = Profile(name,
                                self.dataFolder / name,
                                pfJson)
        try:
            out[self.getCurrentProfileName()].isCurrentProfile = True
        except:
            pass
        return out

    def retrieveCurrentProfile(self, pfMap=None):
        return self.retrieveProfile(self.getCurrentProfileName())

    def retrieveProfile(self, name, pfMap=None):
        if name is None:
            raise ValueError("Cannot retrieve profile")
        if pfMap is None:
            pfMap = self.getAllProfiles()
        if name not in pfMap:
            raise ValueError("Cannot find profile %s" % name)
        return pfMap.get(name)

    def checkProfile(self, pf, raiseIfNotSync=True):
        '''
        Check if a profile contains all needed links to all contained packages
        '''
        env = self.app.getLeafEnvironment()
        env.addSubEnv(self.readConfiguration().getEnvironment())
        env.addSubEnv(pf.getEnvironment())

        try:
            linkedPiList = list(map(
                Manifest.getIdentifier,
                pf.getLinkedPackages()))
            neededPiList = list(map(
                Manifest.getIdentifier,
                self.getProfileDependencies(pf)))

            missingPiList = [pi for pi in neededPiList
                             if pi not in linkedPiList]
            extraPiList = [pi for pi in linkedPiList
                           if pi not in neededPiList]

            if len(extraPiList) > 0 or len(missingPiList) > 0:
                if len(missingPiList) > 0:
                    self.logger.printVerbose("Profile is missing package(s):",
                                             ", ".join(map(str, missingPiList)))
                if len(extraPiList) > 0:
                    self.logger.printVerbose("Profile should not have package(s):",
                                             ", ".join(map(str, extraPiList)))
                raise ValueError("Profile not sync")
        except:
            message = "Profile %s is out of sync, please run 'leaf sync'" % (
                pf.name)
            if raiseIfNotSync:
                raise ValueError(message)
            self.logger.printError(message)
            return False
        return True

    def getCurrentProfileName(self):
        if self.currentLink.is_symlink():
            try:
                return self.currentLink.resolve().name
            except Exception:
                self.currentLink.unlink()
                raise ValueError(
                    "No current profile, you need to select a profile first")
        else:
            raise ValueError(
                "No current profile, you need to select to a profile first")

    def deleteProfile(self, name):
        pf = self.retrieveProfile(name)
        if self.logger.confirm(
                question="Do you want to delete profile %s?" % pf.name):
            wsc = self.readConfiguration()
            del wsc.getProfiles()[pf.name]
            if pf.folder.exists():
                shutil.rmtree(str(pf.folder))
            self.writeConfiguration(wsc)
            if pf.isCurrentProfile:
                self.updateCurrentLink(None)
            return pf

    def createProfile(self, name):
        # Read configuration
        wsc = self.readConfiguration()

        name = Profile.checkValidName(name)

        # Check profile can be created
        if name in wsc.getProfiles():
            raise ValueError("Profile %s already exists" % name)

        # Create & update profile
        self.logger.printDefault("Create profile %s" % name)
        pf = Profile.emptyProfile(name, self.dataFolder / name)

        # Update & save configuration
        wsc.getProfiles()[name] = pf.json
        self.writeConfiguration(wsc)

        # Switch to new profile
        self.switchProfile(name)

        return pf

    def updateProfile(self,
                      name,
                      newName=None,
                      mpkgAddList=None, mpkgRmList=None,
                      envSetMap=None, envUnsetList=None):
        # Retrieve profile
        wsc = self.readConfiguration()
        pf = self.retrieveProfile(name)

        # Check new name is valid in case of rename
        if newName is not None:
            newName = Profile.checkValidName(newName)
            if newName != pf.name and newName in wsc.getProfiles():
                raise ValueError("Profile %s already exists" % newName)

        # Add needed packages
        pkgMap = pf.getPackageMap()
        if mpkgAddList is not None:
            piAddList = self.app.resolveLatest(mpkgAddList,
                                               ipMap=self.app.listInstalledPackages(),
                                               apMap=self.app.listAvailablePackages())
            for pi in piAddList:
                addPi = False
                if pi.name in pkgMap:
                    oldPi = pkgMap[pi.name]
                    if oldPi != pi:
                        addPi = self.logger.confirm(question="Do you want to update package %s from %s to %s?" % (
                            pi.name,
                            oldPi.version,
                            pi.version))
                else:
                    self.logger.printDefault("Add package %s" % (pi))
                    addPi = True
                if addPi:
                    pkgMap[pi.name] = pi

        # Remove needed packages
        if mpkgRmList is not None:
            for mpkg in mpkgRmList:
                pi = None
                if PackageIdentifier.isValidIdentifier(mpkg):
                    pi = PackageIdentifier.fromString(mpkg)
                elif mpkg in pkgMap:
                    pi = pkgMap[mpkg]
                else:
                    raise ValueError("Cannot find package %s in profile %s" %
                                     (mpkg, pf.name))
                self.logger.printDefault("Remove package %s" % (pi))
                del pkgMap[pi.name]

        # replace pkg list
        pf.setPackages(pkgMap.values())

        # Update profile
        pf.updateEnv(setMap=envSetMap,
                     unsetList=envUnsetList)

        # Handle rename
        if newName is not None and newName != pf.name:
            newFolder = self.dataFolder / newName
            if pf.folder.exists():
                pf.folder.rename(newFolder)
            if pf.isCurrentProfile:
                self.updateCurrentLink(newName)
            # Delete the previous profile
            del wsc.getProfiles()[pf.name]
            # Update the name/folder
            pf.name = newName
            pf.folder = newFolder

        # Update & save configuration
        wsc.getProfiles()[pf.name] = pf.json
        self.writeConfiguration(wsc)
        self.checkProfile(pf, raiseIfNotSync=False)
        return pf

    def switchProfile(self, name):
        pf = self.retrieveProfile(name)
        # Check folder exist
        if not pf.folder.exists():
            pf.folder.mkdir(parents=True)
        # Update symlink
        self.updateCurrentLink(pf.name)
        self.logger.printDefault("Current profile is now %s" % pf.name)
        return pf

    def updateCurrentLink(self, name):
        '''
        Update the current link without any check
        '''
        if self.currentLink.is_symlink():
            self.currentLink.unlink()
        if name is not None:
            self.currentLink.symlink_to(name)

    def provisionProfile(self, name):
        pf = self.retrieveProfile(name)
        # Ensure FS clean
        if not self.dataFolder.is_dir():
            self.dataFolder.mkdir()
        elif pf.folder.is_dir():
            shutil.rmtree(str(pf.folder))
        pf.folder.mkdir()

        # Check if packages need to be installed
        missingApList = DependencyManager.compute(pf.getPackageIdentifiers(),
                                                  DependencyType.INSTALL,
                                                  strategy=DependencyStrategy.LATEST_VERSION,
                                                  apMap=self.app.listAvailablePackages(),
                                                  ipMap=self.app.listInstalledPackages(),
                                                  env=self.getSkelEnvironement(pf))

        # Install needed package
        if len(missingApList) > 0:
            env = self.getSkelEnvironement(pf)
            self.app.installFromRemotes(list(map(Manifest.getIdentifier, missingApList)),
                                        env=env)

        # Do all needed links
        profilesDependencyList = self.getProfileDependencies(pf)
        for ip in profilesDependencyList:
            piFolder = pf.folder / ip.getIdentifier().name
            if piFolder.exists():
                piFolder = pf.folder / str(ip.getIdentifier())
            piFolder.symlink_to(ip.folder)

    def getProfileEnv(self, name):
        pf = self.retrieveProfile(name)
        self.checkProfile(pf)
        return packageListToEnvironnement(self.getProfileDependencies(pf),
                                          self.app.listInstalledPackages(),
                                          env=self.getSkelEnvironement(pf))

    def getSkelEnvironement(self, pf=None):
        out = self.app.getLeafEnvironment()
        out.env.append(("LEAF_WORKSPACE", self.rootFolder))
        out.addSubEnv(self.readConfiguration().getEnvironment())
        if pf is not None:
            out.env.append(("LEAF_PROFILE", pf.name))
            out.addSubEnv(pf.getEnvironment())
        return out

    def getProfileDependencies(self, pf):
        '''
        Returns all latest packages needed by a profile
        '''
        return DependencyManager.compute(pf.getPackageIdentifiers(),
                                         DependencyType.INSTALLED,
                                         strategy=DependencyStrategy.LATEST_VERSION,
                                         ipMap=self.app.listInstalledPackages(),
                                         env=self.getSkelEnvironement(pf))

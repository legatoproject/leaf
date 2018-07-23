'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
import os
import shutil

from leaf import __version__
from leaf.constants import LeafFiles, JsonConstants, EnvConstants
from leaf.core.dependencies import DependencyManager, DependencyType,\
    DependencyStrategy
from leaf.model.config import WorkspaceConfiguration
from leaf.model.environment import Environment
from leaf.model.workspace import Profile
from leaf.utils import jsonLoadFile, checkSupportedLeaf, jsonWriteFile
from pathlib import Path


class WorkspaceManager():
    '''
    Represent a workspace, where leaf profiles apply
    '''

    @staticmethod
    def isWorkspaceRoot(folder):
        return folder is not None and (folder / LeafFiles.WS_CONFIG_FILENAME).is_file()

    @staticmethod
    def findRoot(customPath=None, checkEnv=True, checkParents=True):
        # If custom path is given, use it as is
        if customPath is not None:
            return customPath

        # Check env if no custom path given
        if checkEnv and EnvConstants.WORKSPACE_ROOT in os.environ:
            return Path(os.environ[EnvConstants.WORKSPACE_ROOT])

        # Check parents
        if checkParents:
            currentFolder = Path(os.getenv('PWD'))
            if WorkspaceManager.isWorkspaceRoot(currentFolder):
                return currentFolder
            else:
                for parent in currentFolder.parents:
                    if WorkspaceManager.isWorkspaceRoot(parent):
                        return parent

        # Use PWD
        return Path(os.getcwd())

    def __init__(self, rootFolder, packageManager):
        self.packageManager = packageManager
        self.logger = packageManager.logger
        self.rootFolder = rootFolder
        self.configFile = rootFolder / LeafFiles.WS_CONFIG_FILENAME
        self.dataFolder = rootFolder / LeafFiles.WS_DATA_FOLDERNAME
        self.currentLink = self.dataFolder / LeafFiles.CURRENT_PROFILE_LINKNAME

    def isInitialized(self):
        return WorkspaceManager.isWorkspaceRoot(self.rootFolder)

    def inittialize(self):
        if self.isInitialized():
            raise ValueError("Workspace is already initialized")
        self.writeConfiguration(WorkspaceConfiguration({}))

    def readConfiguration(self, initIfNeeded=False):
        '''
        Return the configuration and if current leaf version is supported
        '''
        if not self.isInitialized():
            if not initIfNeeded:
                raise("Workspace is not initialized")
            self.inittialize()
        wsc = WorkspaceConfiguration(jsonLoadFile(self.configFile))
        checkSupportedLeaf(wsc.jsonget(JsonConstants.INFO_LEAF_MINVER),
                           exceptionMessage="Leaf has to be updated to work with this workspace")
        return wsc

    def writeConfiguration(self, wsc):
        '''
        Write the configuration and set the min leaf version to current version
        '''
        if not self.dataFolder.exists():
            self.dataFolder.mkdir()
        wsc.json[JsonConstants.WS_LEAFMINVERSION] = __version__
        tmpFile = self.dataFolder / ("tmp-" + LeafFiles.WS_CONFIG_FILENAME)
        jsonWriteFile(tmpFile, wsc.json, pp=True)
        tmpFile.rename(self.configFile)

    def getWorkspaceEnvironment(self):
        out = self.readConfiguration().getEnvironment()
        out.env.append((EnvConstants.WORKSPACE_ROOT, str(self.rootFolder)))
        return out

    def updateWorkspaceEnv(self, setMap=None, unsetList=None):
        wsc = self.readConfiguration()
        wsc.updateEnv(setMap, unsetList)
        self.writeConfiguration(wsc)

    def listProfiles(self):
        '''
        Return a map(name/profile) of all profiles
        '''
        wsc = self.readConfiguration()
        out = OrderedDict()
        for name, json in wsc.getProfilesMap().items():
            out[name] = Profile(name, self.dataFolder / name, json)
        try:
            out[self.getCurrentProfileName()].isCurrentProfile = True
        except:
            pass
        return out

    def getProfile(self, name):
        if name is None:
            raise ValueError("Cannot find profile")
        pfMap = self.listProfiles()
        if name not in pfMap:
            raise ValueError("Cannot find profile %s" % name)
        return pfMap[name]

    def createProfile(self, name):
        name = Profile.checkValidName(name)
        wsc = self.readConfiguration()
        pfMap = wsc.getProfilesMap()
        if name in pfMap:
            raise ValueError("Profile %s already exists" % name)
        pfMap[name] = {}
        self.writeConfiguration(wsc)
        return self.getProfile(name)

    def renameProfile(self, oldname, newname):
        newname = Profile.checkValidName(newname)

        # Delete data folder
        oldProfile = self.getProfile(oldname)
        oldFolder = oldProfile.folder
        if oldProfile.isCurrentProfile:
            self.updateCurrentLink(None)

        wsc = self.readConfiguration()
        pfMap = wsc.getProfilesMap()
        if oldname not in pfMap:
            raise ValueError("Cannot find oldProfile %s" % oldname)
        if newname in pfMap:
            raise ValueError("Profile %s already exists" % newname)
        pfMap[newname] = pfMap[oldname]
        del pfMap[oldname]
        self.writeConfiguration(wsc)

        newProfile = self.getProfile(newname)
        # Rename old folder
        if newProfile.folder.exists():
            shutil.rmtree(str(newProfile.folder))
        if oldFolder.exists():
            oldFolder.rename(newProfile.folder)
        # Update current link
        if oldProfile.isCurrentProfile:
            self.switchProfile(newProfile)
        return newProfile

    def updateProfile(self, profile):
        wsc = self.readConfiguration()
        pfMap = wsc.getProfilesMap()
        if profile.name not in pfMap:
            raise ValueError("Cannot update profile %s" % profile.name)
        pfMap[profile.name] = profile.json
        self.writeConfiguration(wsc)
        return self.getProfile(profile.name)

    def deleteProfile(self, name):
        # Clean files
        profile = self.getProfile(name)
        if profile.folder.exists():
            shutil.rmtree(str(profile.folder))
        if profile.isCurrentProfile:
            self.updateCurrentLink(None)
        # Update configuration
        wsc = self.readConfiguration()
        pfMap = wsc.getProfilesMap()
        del pfMap[name]
        self.writeConfiguration(wsc)

    def isProfileSync(self, profile, raiseIfNotSync=False):
        '''
        Check if a profile contains all needed links to all contained packages
        '''
        try:
            linkedPiList = [ip.getIdentifier()
                            for ip in profile.getLinkedPackages()]
            neededPiList = [ip.getIdentifier()
                            for ip in self.getProfileDependencies(profile)]
            for pi in neededPiList:
                if pi not in linkedPiList:
                    raise ValueError("Missing package link for %s" % pi)
            for pi in linkedPiList:
                if pi not in neededPiList:
                    raise ValueError("Package should not be linked: %s" % pi)
        except Exception as e:
            if raiseIfNotSync:
                raise e
            self.logger.printVerbose(str(e))
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

    def switchProfile(self, profile):
        # Check folder exist
        if not profile.folder.exists():
            profile.folder.mkdir(parents=True)
        # Update symlink
        self.updateCurrentLink(profile.name)
        self.logger.printDefault("Current profile is now %s" % profile.name)
        return profile

    def updateCurrentLink(self, name):
        '''
        Update the current link without any check
        '''
        if self.currentLink.is_symlink():
            self.currentLink.unlink()
        if name is not None:
            self.currentLink.symlink_to(name)

    def provisionProfile(self, profile):
        # Ensure FS clean
        if not self.dataFolder.is_dir():
            self.dataFolder.mkdir()
        elif profile.folder.is_dir():
            shutil.rmtree(str(profile.folder))
        profile.folder.mkdir()

        # Check if all needed packages are installed
        try:
            self.getProfileDependencies(profile)
            self.logger.printVerbose("All packages are already installed")
        except:
            self.logger.printDefault("Profile is out of sync")
            self.packageManager.installFromRemotes(
                profile.getPackages(),
                env=self._getSkelEnvironement(profile))

        # Do all needed links
        profilesDependencyList = self.getProfileDependencies(profile)
        for ip in profilesDependencyList:
            piFolder = profile.folder / ip.getIdentifier().name
            if piFolder.exists():
                piFolder = profile.folder / str(ip.getIdentifier())
            piFolder.symlink_to(ip.folder)

    def getFullEnvironment(self, profile):
        self.isProfileSync(profile, raiseIfNotSync=True)
        out = self._getSkelEnvironement(profile)
        out.addSubEnv(self.packageManager.getPackagesEnvironment(
            self.getProfileDependencies(profile)))
        return out

    def _getSkelEnvironement(self, profile):
        return Environment.build(
            self.packageManager.getLeafEnvironment(),
            self.packageManager.getUserEnvironment(),
            self.getWorkspaceEnvironment(),
            profile.getEnvironment())

    def getProfileDependencies(self, profile):
        '''
        Returns all latest packages needed by a profile
        '''
        return DependencyManager.compute(
            profile.getPackagesMap().values(),
            DependencyType.INSTALLED,
            strategy=DependencyStrategy.LATEST_VERSION,
            ipMap=self.packageManager.listInstalledPackages(),
            env=self._getSkelEnvironement(profile))

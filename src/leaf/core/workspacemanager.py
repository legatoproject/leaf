'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import os
import shutil
from builtins import Exception
from collections import OrderedDict
from pathlib import Path

from leaf.constants import EnvConstants, LeafFiles
from leaf.core.dependencies import DependencyUtils
from leaf.core.error import InvalidProfileNameException, LeafException, \
    NoProfileSelected, ProfileNameAlreadyExistException, \
    ProfileOutOfSyncException, ProfileProvisioningException, \
    WorkspaceNotInitializedException
from leaf.core.packagemanager import PackageManager
from leaf.model.config import WorkspaceConfiguration
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.model.workspace import Profile


class WorkspaceManager(PackageManager):
    '''
    Represent a workspace, where leaf profiles apply
    '''

    @staticmethod
    def isWorkspaceRoot(folder):
        return folder is not None and (folder / LeafFiles.WS_CONFIG_FILENAME).is_file()

    @staticmethod
    def findRoot(checkEnv=True, checkParents=True):
        # Check env if no custom path given
        if checkEnv and os.getenv(EnvConstants.WORKSPACE_ROOT, "") != "":
            return Path(os.environ[EnvConstants.WORKSPACE_ROOT])

        # Check parents
        if checkParents:
            # Use PWD to avoid symlinks resolution
            currentFolder = Path(os.getenv('PWD'))
            if WorkspaceManager.isWorkspaceRoot(currentFolder):
                return currentFolder
            else:
                for parent in currentFolder.parents:
                    if WorkspaceManager.isWorkspaceRoot(parent):
                        return parent

        # Use PWD
        return Path(os.getcwd())

    def __init__(self, workspaceRootFolder, verbosity):
        PackageManager.__init__(self, verbosity)
        self.workspaceRootFolder = workspaceRootFolder
        self.workspaceConfigFile = workspaceRootFolder / LeafFiles.WS_CONFIG_FILENAME
        self.workspaceDataFolder = workspaceRootFolder / LeafFiles.WS_DATA_FOLDERNAME
        self.currentLink = self.workspaceDataFolder / LeafFiles.CURRENT_PROFILE_LINKNAME

    def isWorkspaceInitialized(self):
        return WorkspaceManager.isWorkspaceRoot(self.workspaceRootFolder)

    def initializeWorkspace(self):
        if self.isWorkspaceInitialized():
            raise LeafException("Workspace is already initialized")
        self.writeWorkspaceConfiguration(WorkspaceConfiguration())

    def readWorkspaceConfiguration(self, initIfNeeded=False):
        '''
        Return the configuration and if current leaf version is supported
        '''
        if not self.isWorkspaceInitialized():
            if not initIfNeeded:
                raise WorkspaceNotInitializedException()
            self.initializeWorkspace()
        return WorkspaceConfiguration(self.workspaceConfigFile)

    def writeWorkspaceConfiguration(self, wsc):
        '''
        Write the configuration and set the min leaf version to current version
        '''
        if not self.workspaceDataFolder.exists():
            self.workspaceDataFolder.mkdir()
        tmpFile = self.workspaceDataFolder / \
            ("tmp-" + LeafFiles.WS_CONFIG_FILENAME)
        wsc.writeLayerToFile(tmpFile, pp=True)
        tmpFile.rename(self.workspaceConfigFile)

    def getWorkspaceEnvironment(self):
        out = self.readWorkspaceConfiguration().getEnvironment()
        out.env.insert(0, (EnvConstants.WORKSPACE_ROOT,
                           str(self.workspaceRootFolder)))
        return out

    def updateWorkspaceEnv(self, setMap=None, unsetList=None):
        wsc = self.readWorkspaceConfiguration()
        wsc.updateEnv(setMap, unsetList)
        self.writeWorkspaceConfiguration(wsc)

    def listProfiles(self):
        '''
        Return a map(name/profile) of all profiles
        '''
        wsc = self.readWorkspaceConfiguration()
        out = OrderedDict()
        for name, json in wsc.getProfilesMap().items():
            out[name] = Profile(name, self.workspaceDataFolder / name, json)
        try:
            out[self.getCurrentProfileName()].isCurrentProfile = True
        except Exception:
            pass
        return out

    def getProfile(self, name):
        if name is None:
            raise LeafException("Cannot find profile")
        pfMap = self.listProfiles()
        if name not in pfMap:
            raise InvalidProfileNameException(name)
        return pfMap[name]

    def createProfile(self, name):
        name = Profile.checkValidName(name)
        wsc = self.readWorkspaceConfiguration()
        pfMap = wsc.getProfilesMap()
        if name in pfMap:
            raise ProfileNameAlreadyExistException(name)
        pfMap[name] = {}
        self.writeWorkspaceConfiguration(wsc)
        return self.getProfile(name)

    def renameProfile(self, oldname, newname):
        newname = Profile.checkValidName(newname)

        # Delete data folder
        oldProfile = self.getProfile(oldname)
        oldFolder = oldProfile.folder
        if oldProfile.isCurrentProfile:
            self.updateCurrentLink(None)

        wsc = self.readWorkspaceConfiguration()
        pfMap = wsc.getProfilesMap()
        if oldname not in pfMap:
            raise InvalidProfileNameException(oldname)
        if newname in pfMap:
            raise ProfileNameAlreadyExistException(newname)
        pfMap[newname] = pfMap[oldname]
        del pfMap[oldname]
        self.writeWorkspaceConfiguration(wsc)

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
        wsc = self.readWorkspaceConfiguration()
        pfMap = wsc.getProfilesMap()
        if profile.name not in pfMap:
            raise LeafException("Cannot update profile %s" % profile.name)
        pfMap[profile.name] = profile.json
        self.writeWorkspaceConfiguration(wsc)
        return self.getProfile(profile.name)

    def deleteProfile(self, name):
        # Clean files
        profile = self.getProfile(name)
        if profile.folder.exists():
            shutil.rmtree(str(profile.folder))
        if profile.isCurrentProfile:
            self.updateCurrentLink(None)
        # Update configuration
        wsc = self.readWorkspaceConfiguration()
        pfMap = wsc.getProfilesMap()
        del pfMap[name]
        self.writeWorkspaceConfiguration(wsc)

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
                    raise LeafException("Missing package link for %s" % pi)
            for pi in linkedPiList:
                if pi not in neededPiList:
                    raise LeafException(
                        "Package should not be linked: %s" % pi)
        except Exception as e:
            if raiseIfNotSync:
                raise ProfileOutOfSyncException(profile, cause=e)
            self.logger.printVerbose(str(e))
            return False
        return True

    def getCurrentProfileName(self):
        if self.currentLink.is_symlink():
            try:
                return self.currentLink.resolve().name
            except Exception:
                self.currentLink.unlink()
                raise NoProfileSelected()
        else:
            raise NoProfileSelected()

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
            self.workspaceConfigFile.touch(exist_ok=True)

    def provisionProfile(self, profile):
        if not profile.folder.is_dir():
            # Create folder if needed
            profile.folder.mkdir(parents=True)
        else:
            # Clean folder content
            for item in profile.folder.glob("*"):
                if item.is_symlink():
                    item.unlink()
                else:
                    shutil.rmtree(str(item))

        # Check if all needed packages are installed
        notInstalledPackages = DependencyUtils.install(
            PackageIdentifier.fromStringList(profile.getPackages()),
            self.listAvailablePackages(),
            self.listInstalledPackages(),
            env=self._getSkelEnvironement(profile))
        if len(notInstalledPackages) == 0:
            self.logger.printVerbose("All packages are already installed")
        else:
            self.logger.printDefault("Profile is out of sync")
            try:
                self.installFromRemotes(
                    PackageIdentifier.fromStringList(profile.getPackages()),
                    env=self._getSkelEnvironement(profile))
            except Exception as e:
                raise ProfileProvisioningException(e)

        # Do all needed links
        profilesDependencyList = self.getProfileDependencies(profile)
        errorCount = 0
        for ip in profilesDependencyList:
            piFolder = profile.folder / ip.getIdentifier().name
            if piFolder.exists():
                piFolder = profile.folder / str(ip.getIdentifier())
            try:
                env = self._getSkelEnvironement(profile)
                self.syncPackages([ip.getIdentifier()], env=env)
                piFolder.symlink_to(ip.folder)
            except Exception as e:
                errorCount += 1
                self.logger.printError(
                    "Error while sync operation on %s" % ip.getIdentifier())
                self.logger.printError(str(e))

        # Touch folder when provisionning is done without error
        if errorCount == 0:
            profile.folder.touch(exist_ok=True)

    def getFullEnvironment(self, profile):
        self.isProfileSync(profile, raiseIfNotSync=True)
        out = self._getSkelEnvironement(profile)
        out.addSubEnv(self.getPackagesEnvironment(
            self.getProfileDependencies(profile)))
        return out

    def _getSkelEnvironement(self, profile):
        return Environment.build(
            self.getBuiltinEnvironment(),
            self.getUserEnvironment(),
            self.getWorkspaceEnvironment(),
            profile.getEnvironment())

    def getProfileDependencies(self, profile):
        '''
        Returns all latest packages needed by a profile
        '''
        return DependencyUtils.installed(
            PackageIdentifier.fromStringList(profile.getPackages()),
            self.listInstalledPackages(),
            onlyKeepLatest=True,
            env=self._getSkelEnvironement(profile))

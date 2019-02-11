'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import json
import os
from builtins import Exception
from collections import OrderedDict
from datetime import datetime
from tempfile import NamedTemporaryFile

import gnupg

from leaf.api.base import LoggerManager
from leaf.core.constants import (JsonConstants, LeafConstants, LeafFiles,
                                 LeafSettings)
from leaf.core.error import (BadRemoteUrlException, LeafException,
                             LeafOutOfDateException, NoEnabledRemoteException,
                             NoRemoteException)
from leaf.core.jsonutils import jsonLoadFile, jsonWriteFile
from leaf.core.utils import downloadData, versionComparator_lt
from leaf.model.package import AvailablePackage
from leaf.model.remote import Remote


class GPGManager(LoggerManager):

    def __init__(self):
        LoggerManager.__init__(self)
        self.gpg = None
        self.gpgHome = self.configurationFolder / LeafFiles.GPG_DIRNAME
        self.gpgDefaultKeyserver = LeafSettings.GPG_KEYSERVER.value

    def __getInitializedGpg(self):
        if self.gpg is None:
            if not self.gpgHome.is_dir():
                self.gpgHome.mkdir(mode=0o700)
            self.gpg = gnupg.GPG(gnupghome=str(self.gpgHome))
        return self.gpg

    def gpgVerifyContent(self, data, sigUrl, expectedKey=None):
        self.logger.printVerbose("Known GPG keys:", len(
            self.__getInitializedGpg().list_keys()))
        with NamedTemporaryFile() as sigFile:
            downloadData(sigUrl, sigFile.name)
            verif = self.__getInitializedGpg().verify_data(sigFile.name, data)
            if verif.valid:
                self.logger.printVerbose(
                    "Content has been signed by %s (%s)" %
                    (verif.username, verif.pubkey_fingerprint))
                if expectedKey is not None:
                    if expectedKey != verif.pubkey_fingerprint:
                        raise LeafException(
                            "Content is not signed with %s" % expectedKey)
            else:
                raise LeafException("Signed content could not be verified")

    def gpgImportKeys(self, *keys, keyserver=None):
        if keyserver is None:
            keyserver = self.gpgDefaultKeyserver
        if len(keys) > 0:
            self.logger.printVerbose("Update GPG keys for %s from %s" %
                                     (", ".join(keys), keyserver))
            gpgImport = self.__getInitializedGpg().recv_keys(keyserver, *keys)
            for result in gpgImport.results:
                if 'ok' in result:
                    self.logger.printVerbose(
                        "Received GPG key {fingerprint}".format(**result))
                else:
                    raise LeafException(
                        "Error receiving GPG keys: {text}".format(**result))


class RemoteManager(GPGManager):

    def __init__(self):
        GPGManager.__init__(self)
        '''
        Constructor
        '''
        self.remoteCacheFile = self.cacheFolder / \
            LeafFiles.CACHE_REMOTES_FILENAME

    def cleanRemotesCacheFile(self):
        if self.remoteCacheFile.exists():
            os.remove(str(self.remoteCacheFile))

    def listRemotes(self, onlyEnabled=False):
        out = OrderedDict()

        cache = None
        if self.remoteCacheFile.exists():
            cache = jsonLoadFile(self.remoteCacheFile)

        items = self.readConfiguration().getRemotesMap().items()
        if len(items) == 0:
            raise NoRemoteException()
        for alias, jsondata in items:
            remote = Remote(alias, jsondata)
            if remote.isEnabled() or not onlyEnabled:
                out[alias] = remote
            url = remote.getUrl()
            if cache is not None and url in cache:
                remote.content = cache[url]

        if len(out) == 0 and onlyEnabled:
            raise NoEnabledRemoteException()
        return out

    def createRemote(self, alias, url, enabled=True, insecure=False, gpgKey=None):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if alias in remotes:
            raise LeafException("Remote %s already exists" % alias)
        if insecure:
            remotes[alias] = {JsonConstants.CONFIG_REMOTE_URL: str(url),
                              JsonConstants.CONFIG_REMOTE_ENABLED: enabled}
        elif gpgKey is not None:
            remotes[alias] = {JsonConstants.CONFIG_REMOTE_URL: str(url),
                              JsonConstants.CONFIG_REMOTE_ENABLED: enabled,
                              JsonConstants.CONFIG_REMOTE_GPGKEY: gpgKey}
        else:
            raise LeafException("Invalid security for remote %s" % alias)
        # Save and clean cache
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def renameRemote(self, oldalias, newalias):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if oldalias not in remotes:
            raise LeafException("Cannot find remote %s" % oldalias)
        if newalias in remotes:
            raise LeafException("Remote %s already exists" % newalias)
        remotes[newalias] = remotes[oldalias]
        del remotes[oldalias]
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def updateRemote(self, remote):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if remote.alias not in remotes:
            raise LeafException("Cannot find remote %s" % remote.alias)
        remotes[remote.alias] = remote.json
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def deleteRemote(self, alias):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if alias not in remotes:
            raise LeafException("Cannot find remote %s" % alias)
        del remotes[alias]
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def fetchRemotes(self, smartRefresh=True):
        '''
        Refresh remotes content with smart refresh, ie auto refresh after X days
        '''
        if self.remoteCacheFile.exists():
            if not smartRefresh:
                os.remove(str(self.remoteCacheFile))
            elif datetime.fromtimestamp(self.remoteCacheFile.stat().st_mtime) < datetime.now() - LeafConstants.CACHE_DELTA:
                self.logger.printDefault("Cache file is outdated")
                os.remove(str(self.remoteCacheFile))
        if not self.remoteCacheFile.exists():
            self.logger.printDefault("Refreshing available packages...")
            content = OrderedDict()
            remotes = self.listRemotes(onlyEnabled=True)
            if len(remotes) == 0:
                raise NoRemoteException()
            for alias, remote in remotes.items():
                try:
                    indexUrl = remote.getUrl()
                    data = downloadData(indexUrl)
                    gpgKey = remote.getGpgKey()
                    if gpgKey is not None:
                        signatureUrl = indexUrl + LeafConstants.GPG_SIG_EXTENSION
                        self.logger.printDefault(
                            "Verifying signature for remote %s" % alias)
                        self.gpgImportKeys(gpgKey)
                        self.gpgVerifyContent(data,
                                              signatureUrl,
                                              expectedKey=gpgKey)
                    self.logger.printVerbose("Fetched", indexUrl)
                    jsonData = json.loads(data.decode())
                    self._checkRemoteContent(alias, indexUrl, jsonData)
                    content[indexUrl] = jsonData
                    self.logger.printDefault(
                        "Fetched content from %s" % alias)
                except LeafOutOfDateException:
                    raise
                except Exception as e:
                    self.printException(BadRemoteUrlException(remote, e))
            if len(content) > 0:
                jsonWriteFile(self.remoteCacheFile, content)

    def _checkRemoteContent(self, alias, url, jsonContent):
        # Check leaf min version for all packages
        remote = Remote("", None)
        remote.content = jsonContent
        leafMinVersion = None
        for apInfoJson in remote.getAvailablePackageList():
            ap = AvailablePackage(apInfoJson, url)
            if not ap.isSupportedByCurrentLeafVersion():
                if leafMinVersion is None or versionComparator_lt(leafMinVersion, ap.getSupportedLeafVersion()):
                    leafMinVersion = ap.getSupportedLeafVersion()
        if leafMinVersion is not None:
            raise LeafOutOfDateException(
                "You need to upgrade leaf v%s to use packages from %s" % (leafMinVersion, alias))

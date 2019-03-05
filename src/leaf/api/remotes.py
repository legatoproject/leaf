"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import os
from builtins import Exception
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import gnupg

from leaf.api.base import LoggerManager
from leaf.core.constants import JsonConstants, LeafConstants, LeafFiles, LeafSettings
from leaf.core.error import BadRemoteUrlException, LeafException, LeafOutOfDateException, NoEnabledRemoteException, NoRemoteException
from leaf.core.jsonutils import jloadfile, jloads, jwritefile
from leaf.core.utils import check_leaf_min_version, download_data, version_comparator_lt
from leaf.model.remote import Remote


class GPGManager(LoggerManager):
    def __init__(self):
        LoggerManager.__init__(self)
        self.__gpg = None
        self.__gpg_home = self.find_configuration_file(LeafFiles.GPG_DIRNAME)
        self.__gpg_keyserver = LeafSettings.GPG_KEYSERVER.value

    @property
    def gpg(self):
        if self.__gpg is None:
            if not self.__gpg_home.is_dir():
                self.__gpg_home.mkdir(mode=0o700)
            self.__gpg = gnupg.GPG(gnupghome=str(self.__gpg_home))
        return self.__gpg

    def gpg_verify_content(self, data, sigurl, expected_key=None):
        self.logger.print_verbose("Known GPG keys: {count}".format(count=len(self.gpg.list_keys())))
        with NamedTemporaryFile() as sigfile:
            download_data(sigurl, Path(sigfile.name))
            verif = self.gpg.verify_data(sigfile.name, data)
            if verif.valid:
                self.logger.print_verbose("Content has been signed by {verif.username} ({verif.pubkey_fingerprint})".format(verif=verif))
                if expected_key is not None:
                    if expected_key != verif.pubkey_fingerprint:
                        raise LeafException("Content is not signed with {key}".format(key=expected_key))
            else:
                raise LeafException("Signed content could not be verified")

    def gpg_import_keys(self, *keys, keyserver=None):
        if keyserver is None:
            keyserver = self.__gpg_keyserver
        if len(keys) > 0:
            self.logger.print_verbose("Update GPG keys for {keys} from {server}".format(keys=", ".join(keys), server=keyserver))
            gpg_import = self.gpg.recv_keys(keyserver, *keys)
            for result in gpg_import.results:
                if "ok" in result:
                    self.logger.print_verbose("Received GPG key {fingerprint}".format(**result))
                else:
                    raise LeafException("Error receiving GPG keys: {text}".format(**result))


class RemoteManager(GPGManager):
    def __init__(self):
        GPGManager.__init__(self)

    @property
    def remote_cache_file(self):
        return self.cache_folder / LeafFiles.CACHE_REMOTES_FILENAME

    def clean_remotes_cache_file(self):
        if self.remote_cache_file.exists():
            os.remove(str(self.remote_cache_file))

    def list_remotes(self, only_enabled=False):
        out = OrderedDict()

        cache = None
        if self.remote_cache_file.exists():
            cache = jloadfile(self.remote_cache_file)
        remotes = self.read_user_configuration().remotes
        if len(remotes) == 0:
            raise NoRemoteException()
        for alias, json in remotes.items():
            remote = Remote(alias, json)
            if remote.enabled or not only_enabled:
                out[alias] = remote
                if cache is not None:
                    remote.content = cache.get(remote.url)

        if len(out) == 0 and only_enabled:
            raise NoEnabledRemoteException()

        return out

    def create_remote(self, alias, url, enabled=True, insecure=False, gpgkey=None):
        usrc = self.read_user_configuration()
        remotes = usrc.remotes
        if alias in remotes:
            raise LeafException("Remote {alias} already exists".format(alias=alias))
        if insecure:
            remotes[alias] = {JsonConstants.CONFIG_REMOTE_URL: str(url), JsonConstants.CONFIG_REMOTE_ENABLED: enabled}
        elif gpgkey is not None:
            remotes[alias] = {
                JsonConstants.CONFIG_REMOTE_URL: str(url),
                JsonConstants.CONFIG_REMOTE_ENABLED: enabled,
                JsonConstants.CONFIG_REMOTE_GPGKEY: gpgkey,
            }
        else:
            raise LeafException("Invalid security for remote {alias}".format(alias=alias))
        # Save and clean cache
        self.write_user_configuration(usrc)
        self.clean_remotes_cache_file()

    def rename_remote(self, oldalias, newalias):
        usrc = self.read_user_configuration()
        remotes = usrc.remotes
        if oldalias not in remotes:
            raise LeafException("Cannot find remote {alias}".format(alias=oldalias))
        if newalias in remotes:
            raise LeafException("Remote {alias} already exists".format(alias=newalias))
        remotes[newalias] = remotes[oldalias]
        del remotes[oldalias]
        self.write_user_configuration(usrc)
        self.clean_remotes_cache_file()

    def update_remote(self, remote):
        usrc = self.read_user_configuration()
        remotes = usrc.remotes
        if remote.alias not in remotes:
            raise LeafException("Cannot find remote {remote.alias}".format(remote=remote))
        remotes[remote.alias] = remote.json
        self.write_user_configuration(usrc)
        self.clean_remotes_cache_file()

    def delete_remote(self, alias):
        usrc = self.read_user_configuration()
        remotes = usrc.remotes
        if alias not in remotes:
            raise LeafException("Cannot find remote {alias}".format(alias=alias))
        del remotes[alias]
        self.write_user_configuration(usrc)
        self.clean_remotes_cache_file()

    def fetch_remotes(self, smart_refresh=True):
        """
        Refresh remotes content with smart refresh, ie auto refresh after X days
        """
        if self.remote_cache_file.exists():
            if not smart_refresh:
                os.remove(str(self.remote_cache_file))
            elif datetime.fromtimestamp(self.remote_cache_file.stat().st_mtime) < datetime.now() - LeafConstants.CACHE_DELTA:
                self.logger.print_default("Cache file is outdated")
                os.remove(str(self.remote_cache_file))
        if not self.remote_cache_file.exists():
            self.logger.print_default("Refreshing available packages...")
            content = OrderedDict()
            remotes = self.list_remotes(only_enabled=True)
            if len(remotes) == 0:
                raise NoRemoteException()
            for alias, remote in remotes.items():
                try:
                    remote_data = download_data(remote.url)
                    gpgkey = remote.gpg_key
                    if gpgkey is not None:
                        signatureurl = remote.url + LeafConstants.GPG_SIG_EXTENSION
                        self.logger.print_default("Verifying signature for remote {alias}".format(alias=alias))
                        self.gpg_import_keys(gpgkey)
                        self.gpg_verify_content(remote_data, signatureurl, expected_key=gpgkey)
                    self.logger.print_verbose("Fetched {remote.url}".format(remote=remote))
                    remote.content = jloads(remote_data.decode())
                    self.__check_remote_content(remote)
                    content[remote.url] = remote.content
                    self.logger.print_default("Fetched content from {alias}".format(alias=alias))
                except LeafOutOfDateException:
                    raise
                except Exception as e:
                    self.print_exception(BadRemoteUrlException(remote, e))
            if len(content) > 0:
                jwritefile(self.remote_cache_file, content)

    def __check_remote_content(self, remote):
        # Check leaf min version for all packages
        expected_minver = None
        for ap in remote.available_packages:
            if ap.leaf_min_version is not None:
                if expected_minver is None or version_comparator_lt(expected_minver, ap.leaf_min_version):
                    expected_minver = ap.leaf_min_version
        check_leaf_min_version(
            expected_minver,
            exception_message="You need to upgrade leaf v{version} to use packages from {remote.alias}".format(version=expected_minver, remote=remote),
        )

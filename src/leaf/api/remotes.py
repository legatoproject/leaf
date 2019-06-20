"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from builtins import Exception
from collections import OrderedDict
from pathlib import Path

import gnupg

from leaf.api.base import LoggerManager
from leaf.core.constants import JsonConstants, LeafConstants, LeafFiles, LeafSettings
from leaf.core.download import download_file
from leaf.core.error import LeafException, NoEnabledRemoteException, NoRemoteException, RemoteFetchException
from leaf.core.jsonutils import jloadfile
from leaf.core.utils import mkdirs
from leaf.model.modelutils import check_leaf_min_version
from leaf.model.remote import Remote


class GPGManager(LoggerManager):
    def __init__(self):
        LoggerManager.__init__(self)
        self.__gpg = None
        self.__gpg_home = self.find_configuration_file(LeafFiles.GPG_DIRNAME)

    @property
    def gpg(self):
        if self.__gpg is None:
            if not self.__gpg_home.is_dir():
                self.__gpg_home.mkdir(mode=0o700)
            self.__gpg = gnupg.GPG(gnupghome=str(self.__gpg_home))
        return self.__gpg

    def gpg_verify_file(self, data: Path, sig: Path, expected_key=None):
        self.logger.print_verbose("Known GPG keys: {count}".format(count=len(self.gpg.list_keys())))
        with sig.open("rb") as sigfile:
            verif = self.gpg.verify_file(sigfile, str(data))
            if verif.valid:
                self.logger.print_verbose("Content has been signed by {verif.username} ({verif.pubkey_fingerprint})".format(verif=verif))
                if expected_key is not None:
                    if expected_key != verif.pubkey_fingerprint:
                        raise LeafException("Content is not signed with {key}".format(key=expected_key))
            else:
                raise LeafException("Signed content could not be verified")

    def gpg_import_keys(self, *keys: str, keyserver: str = None):
        if keyserver is None:
            keyserver = LeafSettings.GPG_KEYSERVER.value
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
    def remote_cache_folder(self):
        return mkdirs(self.cache_folder / LeafFiles.CACHE_REMOTES_FOLDERNAME)

    def __clean_remote_files(self, alias: str):
        for f in self.__get_remote_files(alias):
            if f.exists():
                f.unlink()

    def __get_remote_files(self, alias: str):
        return (
            self.remote_cache_folder / "{alias}{ext}".format(alias=alias, ext=".json"),
            self.remote_cache_folder / "{alias}{ext}".format(alias=alias, ext=LeafConstants.GPG_SIG_EXTENSION),
        )

    def list_remotes(self, only_enabled: bool = False):
        out = OrderedDict()
        remotes = self.read_user_configuration().remotes
        if len(remotes) == 0:
            raise NoRemoteException()
        for alias, json in remotes.items():
            remote = Remote(alias, json)
            if remote.enabled or not only_enabled:
                out[alias] = remote
                rindex, rsig = self.__get_remote_files(alias)
                # Load content if cache exists and check signature is present if needed
                if rindex.exists() and (remote.gpg_key is None or rsig.exists()):
                    try:
                        remote.content = jloadfile(rindex)
                    except Exception:
                        self.logger.print_default("Invalid json file cache for remote {alias}".format(alias=alias))
                        self.__clean_remote_files(alias)
        if len(out) == 0 and only_enabled:
            raise NoEnabledRemoteException()

        return out

    def create_remote(self, alias: str, url: str, enabled: bool = True, insecure: bool = False, gpgkey: str = None):
        with self.open_user_configuration() as usrc:
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
        self.__clean_remote_files(alias)

    def rename_remote(self, oldalias: str, newalias: str):
        with self.open_user_configuration() as usrc:
            remotes = usrc.remotes
            if oldalias not in remotes:
                raise LeafException("Cannot find remote {alias}".format(alias=oldalias))
            if newalias in remotes:
                raise LeafException("Remote {alias} already exists".format(alias=newalias))
            remotes[newalias] = remotes[oldalias]
            del remotes[oldalias]
        self.__clean_remote_files(oldalias)
        self.__clean_remote_files(newalias)

    def update_remote(self, remote: Remote):
        with self.open_user_configuration() as usrc:
            remotes = usrc.remotes
            if remote.alias not in remotes:
                raise LeafException("Cannot find remote {remote.alias}".format(remote=remote))
            remotes[remote.alias] = remote.json
        self.__clean_remote_files(remote.alias)

    def delete_remote(self, alias: str):
        with self.open_user_configuration() as usrc:
            remotes = usrc.remotes
            if alias not in remotes:
                raise LeafException("Cannot find remote {alias}".format(alias=alias))
            del remotes[alias]
        self.__clean_remote_files(alias)

    def __fetch_remote(self, remote: Remote):
        # clean files if they exist
        self.__clean_remote_files(remote.alias)
        # Target files
        index, sig = self.__get_remote_files(remote.alias)
        try:
            # Download index
            self.logger.print_default("Fetching remote {remote.alias}".format(remote=remote))
            download_file(remote.url, index)
            # If gpg enabled
            gpgkey = remote.gpg_key
            if gpgkey is not None:
                download_file(remote.url + LeafConstants.GPG_SIG_EXTENSION, sig)
                self.logger.print_default("Verifying signature for remote {0.alias}".format(remote))
                self.gpg_import_keys(gpgkey)
                self.gpg_verify_file(index, sig, expected_key=gpgkey)
            remote.content = jloadfile(index)
            self.__check_remote_content(remote)
        except Exception as e:
            self.__clean_remote_files(remote.alias)
            self.print_exception(RemoteFetchException(remote, e))

    def fetch_remotes(self, force_refresh: bool = False):
        """
        Refresh remotes content with smart refresh, ie auto refresh after X days
        """
        remotes = self.list_remotes(only_enabled=True)
        if len(remotes) == 0:
            raise NoRemoteException()
        for alias, remote in remotes.items():
            rindex, _sig = self.__get_remote_files(alias)
            if not force_refresh and rindex.exists():
                if self.is_file_outdated(rindex):
                    self.logger.print_verbose("Cache for remote {0} is outdated".format(alias))
                else:
                    # Smart refresh skip refresh for current remote
                    continue
            self.__fetch_remote(remote)

    def __check_remote_content(self, remote: Remote):
        # Check leaf min version for all packages
        expected_minver = check_leaf_min_version(remote.available_packages)
        if expected_minver is not None and not self.logger.isquiet():
            self.print_hints(
                "You need to upgrade leaf to v{version} to use some packages from remote {remote.alias}".format(version=expected_minver, remote=remote)
            )

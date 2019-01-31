'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import os
from datetime import timedelta
from pathlib import Path


class EnvConstants():
    # Settings
    DOWNLOAD_TIMEOUT = 'LEAF_TIMEOUT'
    DEBUG_MODE = 'LEAF_DEBUG'
    GPG_KEYSERVER = "LEAF_GPG_KEYSERVER"
    NON_INTERACTIVE = 'LEAF_NON_INTERACTIVE'
    CUSTOM_TAR = 'LEAF_TAR_BIN'
    DISABLE_LOCKS = 'LEAF_DISABLE_LOCKS'
    CUSTOM_THEME = 'LEAF_THEME'
    PAGER = 'LEAF_PAGER'
    NOPLUGIN = 'LEAF_NOPLUGIN'

    '''
    Leaf settings are some env vars that user can configure either in is environment or in user scope
    For example, LEAF_DEBUG can be set to 1 with:
    $ LEAF_DEBUG=1 leaf search
    --or--
    $ leaf env user --set LEAF_DEBUG=1
    $ leaf search
    '''
    LEAF_SETTINGS = (DOWNLOAD_TIMEOUT,
                     DEBUG_MODE,
                     GPG_KEYSERVER,
                     NON_INTERACTIVE,
                     CUSTOM_TAR,
                     DISABLE_LOCKS,
                     CUSTOM_THEME,
                     PAGER,
                     NOPLUGIN)

    # Other env variables
    WORKSPACE_ROOT = 'LEAF_WORKSPACE'
    CUSTOM_CONFIG = 'LEAF_CONFIG'
    CUSTOM_CACHE = 'LEAF_CACHE'
    CUSTOM_RESOURCES = 'LEAF_RESOURCES'


class LeafConstants():
    '''
    Constants needed by Leaf
    '''
    DEFAULT_ERROR_RC = 2
    MIN_PYTHON_VERSION = (3, 4)
    COLORAMA_MIN_VERSION = "0.3.3"
    DEFAULT_DOWNLOAD_TIMEOUT = "10"
    DEFAULT_PROFILE = "default"
    CACHE_DELTA = timedelta(days=1)
    CACHE_SIZE_MAX = 5 * 1024 * 1024 * 1024  # 5GB
    GPG_SIG_EXTENSION = '.asc'
    DEFAULT_GPG_KEYSERVER = 'subset.pool.sks-keyservers.net'
    LATEST = "latest"
    DEFAULT_PAGER = pager = ("less", "-R", "-S", "-P",
                             "Leaf -- Press q to exit")
    DEFAULT_SHELL = 'bash'


class LeafFiles():
    '''
    Files & Folders used by Leaf
    '''
    MANIFEST = 'manifest.json'
    # Workspace
    WS_CONFIG_FILENAME = "leaf-workspace.json"
    WS_DATA_FOLDERNAME = "leaf-data"
    CURRENT_PROFILE_LINKNAME = "current"
    # Configuration folders
    ETC_PREFIX = Path("/etc/leaf")
    DEFAULT_LEAF_ROOT = Path(os.path.expanduser("~/.leaf"))
    DEFAULT_CONFIG_FOLDER = Path(os.path.expanduser("~/.config/leaf"))
    DEFAULT_CACHE_FOLDER = Path(os.path.expanduser("~/.cache/leaf"))
    # Configuration files
    CONFIG_FILENAME = 'config.json'
    CACHE_DOWNLOAD_FOLDERNAME = "files"
    CACHE_REMOTES_FILENAME = 'remotes.json'
    THEMES_FILENAME = 'themes.ini'
    PLUGINS_DIRNAME = 'plugins'
    SHELL_DIRNAME = 'shell'
    GPG_DIRNAME = 'gpg'
    LOCK_FILENAME = 'lock'
    # Releng
    EXTINFO_EXTENSION = '.info'

    @staticmethod
    def getConfigFolder():
        out = LeafFiles.DEFAULT_CONFIG_FOLDER
        value = os.getenv(EnvConstants.CUSTOM_CONFIG, "")
        if len(value) > 0:
            out = Path(value)
        if not out.is_dir():
            out.mkdir(parents=True)
        return out

    @staticmethod
    def getCacheFolder():
        out = LeafFiles.DEFAULT_CACHE_FOLDER
        value = os.getenv(EnvConstants.CUSTOM_CACHE, "")
        if len(value) > 0:
            out = Path(value)
        if not out.is_dir():
            out.mkdir(parents=True)
        return out

    @staticmethod
    def getResource(name: str = None, check_exists=True):
        folder = None
        for prefix in (os.getenv(EnvConstants.CUSTOM_RESOURCES, ""),
                       os.path.expanduser("~/.local/share/leaf"),
                       "/usr/share/leaf"):
            if len(prefix) > 0:
                folder = Path(prefix)
                if folder.is_dir():
                    break
        out = folder if name is None else folder / name
        if check_exists and not out.exists():
            return None
        return out


class JsonConstants(object):
    '''
    Constants for Json grammar
    '''
    # Configuration
    CONFIG_REMOTES = 'remotes'
    CONFIG_REMOTE_URL = 'url'
    CONFIG_REMOTE_ENABLED = 'enabled'
    CONFIG_REMOTE_GPGKEY = 'gpgKey'
    CONFIG_ENV = 'env'
    CONFIG_ROOT = 'rootfolder'

    # Index
    REMOTE_NAME = 'name'
    REMOTE_DATE = 'date'
    REMOTE_DESCRIPTION = 'description'
    REMOTE_PACKAGES = 'packages'
    REMOTE_PACKAGE_SIZE = 'size'
    REMOTE_PACKAGE_FILE = 'file'
    REMOTE_PACKAGE_HASH = 'hash'

    # Manifest
    INFO = 'info'
    INFO_NAME = 'name'
    INFO_VERSION = 'version'
    INFO_DATE = 'date'
    INFO_LEAF_MINVER = 'leafMinVersion'
    INFO_DEPENDS = 'depends'
    INFO_REQUIRES = 'requires'
    INFO_MASTER = 'master'
    INFO_DESCRIPTION = 'description'
    INFO_TAGS = 'tags'
    INFO_FEATURES = 'features'
    INFO_FEATURE_DESCRIPTION = 'description'
    INFO_FEATURE_KEY = 'key'
    INFO_FEATURE_VALUES = 'values'
    INFO_AUTOUPGRADE = 'upgrade'
    INSTALL = 'install'
    SYNC = 'sync'
    UNINSTALL = 'uninstall'
    STEP_LABEL = 'label'
    STEP_IGNORE_FAIL = 'ignoreFail'
    STEP_EXEC_ENV = 'env'
    STEP_EXEC_COMMAND = 'command'
    STEP_EXEC_VERBOSE = 'verbose'
    STEP_EXEC_SHELL = 'shell'
    ENV = 'env'
    ENTRYPOINTS = 'bin'
    ENTRYPOINT_PATH = 'path'
    ENTRYPOINT_DESCRIPTION = 'description'
    ENTRYPOINT_SHELL = 'shell'
    PLUGINS = 'plugins'
    PLUGIN_PREFIX = 'location'
    PLUGIN_DESCRIPTION = 'description'
    PLUGIN_SOURCE = 'source'
    PLUGIN_CLASS = 'class'

    # Profiles
    WS_PROFILES = "profiles"
    WS_LEAFMINVERSION = "leafMinVersion"
    WS_ENV = "env"
    WS_REMOTES = "remotes"
    WS_PROFILE_PACKAGES = "packages"
    WS_PROFILE_ENV = "env"

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

from leaf.core.settings import RegexValidator, Setting, StaticSettings


class CommonSettings(StaticSettings):
    WORKSPACE = Setting('LEAF_WORKSPACE')
    CONFIG_FOLDER = Setting('LEAF_CONFIG',
                            os.path.expanduser("~/.config/leaf"))
    CACHE_FOLDER = Setting('LEAF_CACHE',
                           os.path.expanduser("~/.cache/leaf"))
    RESOURCES_FOLDER = Setting('LEAF_RESOURCES')


class LeafSettings(CommonSettings):
    '''
    Leaf settings are some env vars that user can configure either in is environment or in user scope
    For example, LEAF_DEBUG can be set to 1 with:
    $ LEAF_DEBUG=1 leaf search
    --or--
    $ leaf env user --set LEAF_DEBUG=1
    $ leaf search
    '''
    DOWNLOAD_TIMEOUT = Setting('LEAF_TIMEOUT', "5",
                               RegexValidator("[0-9]+"))
    DOWNLOAD_RETRY = Setting('LEAF_RETRY', "5",
                             RegexValidator("[0-9]+"))
    DOWNLOAD_RESUME = Setting('LEAF_RESUME', "1")
    DEBUG_MODE = Setting('LEAF_DEBUG')
    GPG_KEYSERVER = Setting('LEAF_GPG_KEYSERVER',
                            "subset.pool.sks-keyservers.net")
    NON_INTERACTIVE = Setting('LEAF_NON_INTERACTIVE')
    TAR_BINARY = Setting('LEAF_TAR_BIN',
                         "tar")
    DISABLE_LOCKS = Setting('LEAF_DISABLE_LOCKS')
    CUSTOM_THEME = Setting('LEAF_THEME')
    PAGER = Setting('LEAF_PAGER')
    NOPLUGIN = Setting('LEAF_NOPLUGIN')
    VERBOSITY = Setting('LEAF_VERBOSE',
                        "default")


class LeafConstants():
    '''
    Constants needed by Leaf
    '''
    DEFAULT_ERROR_RC = 2
    MIN_PYTHON_VERSION = (3, 4)
    COLORAMA_MIN_VERSION = "0.3.3"
    DEFAULT_PROFILE = "default"
    CACHE_DELTA = timedelta(days=1)
    CACHE_SIZE_MAX = 5 * 1024 * 1024 * 1024  # 5GB
    GPG_SIG_EXTENSION = '.asc'
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
    USER_RESOURCE_FOLDER = Path(os.path.expanduser("~/.local/share/leaf"))
    SYSTEM_RESOURCE_FOLDER = Path("/usr/share/leaf")
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
    def getResource(name: str = None, check_exists=True):
        folder = None
        if LeafSettings.RESOURCES_FOLDER.is_set():
            folder = Path(LeafSettings.RESOURCES_FOLDER.value)
        elif LeafFiles.USER_RESOURCE_FOLDER.is_dir():
            folder = LeafFiles.USER_RESOURCE_FOLDER
        else:
            folder = LeafFiles.SYSTEM_RESOURCE_FOLDER

        if not folder.is_dir():
            raise ValueError(
                "Cannot find leaf resources folder: %s" % folder)

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

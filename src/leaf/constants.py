'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from datetime import timedelta
from pathlib import Path
import os


class EnvConstants():
    '''
    Leaf specific env vars
    '''
    WORKSPACE_ROOT = 'LEAF_WORKSPACE'
    CUSTOM_CONFIG = 'LEAF_CONFIG'
    CUSTOM_CACHE = 'LEAF_CACHE'
    DOWNLOAD_TIMEOUT = 'LEAF_TIMEOUT'
    DEBUG_MODE = 'LEAF_DEBUG'
    GPG_KEYSERVER = "LEAF_GPG_KEYSERVER"


class LeafConstants():
    '''
    Constants needed by Leaf
    '''
    MIN_PYTHON_VERSION = (3, 4)
    DOWNLOAD_TIMEOUT = int(os.environ.get(EnvConstants.DOWNLOAD_TIMEOUT,
                                          "5"))
    LEAF_COMPRESSION = {'.leaf': 'xz',
                        '.tar':  '',
                        '.xz':   'xz',
                        '.bz2':  'bz2',
                        '.tgz':  'gz',
                        '.gz':   'gz'}
    DEFAULT_PROFILE = "default"
    CACHE_DELTA = timedelta(days=1)
    GPG_SIG_EXTENSION = '.asc'
    DEFAULT_GPG_KEYSERVER = 'subset.pool.sks-keyservers.net'


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
    USER_HOME = Path(os.path.expanduser("~"))
    DEFAULT_LEAF_ROOT = USER_HOME / '.leaf'
    DEFAULT_CONFIG_FOLDER = USER_HOME / '.config' / 'leaf'
    DEFAULT_CACHE_FOLDER = USER_HOME / '.cache' / 'leaf'
    # Configuration files
    CONFIG_FILENAME = 'config.json'
    CACHE_DOWNLOAD_FOLDERNAME = "files"
    CACHE_REMOTES_FILENAME = 'remotes.json'
    THEMES_FILENAME = 'themes.ini'
    GPG_DIRNAME = 'gpg'
    # Skeleton files
    SKEL_FILES = {
        CONFIG_FILENAME: [
            Path('/') / 'etc' / 'leaf' / CONFIG_FILENAME,
            Path('/') / 'usr' / 'share' / 'leaf' / CONFIG_FILENAME,
            USER_HOME / '.local' / 'share' / 'leaf' / CONFIG_FILENAME],
        THEMES_FILENAME: [
            Path('/') / 'etc' / 'leaf' / THEMES_FILENAME,
            Path('/') / 'usr' / 'share' / 'leaf' / THEMES_FILENAME,
            USER_HOME / '.local' / 'share' / 'leaf' / THEMES_FILENAME],
    }


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
    INSTALL = 'install'
    SYNC = 'sync'
    UNINSTALL = 'uninstall'
    STEP_LABEL = 'label'
    STEP_IGNORE_FAIL = 'ignoreFail'
    STEP_EXEC_ENV = 'env'
    STEP_EXEC_COMMAND = 'command'
    STEP_EXEC_VERBOSE = 'verbose'
    ENV = 'env'

    # Profiles
    WS_PROFILES = "profiles"
    WS_LEAFMINVERSION = "leafMinVersion"
    WS_ENV = "env"
    WS_REMOTES = "remotes"
    WS_PROFILE_PACKAGES = "packages"
    WS_PROFILE_ENV = "env"

'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from datetime import timedelta
import os
from pathlib import Path


class LeafConstants():
    '''
    Constants needed by Leaf
    '''
    MIN_PYTHON_VERSION = (3, 4)
    MANIFEST = 'manifest.json'
    DOWNLOAD_TIMEOUT = int(os.environ.get("LEAF_TIMEOUT", "5"))
    LEAF_COMPRESSION = {'.leaf': 'xz',
                        '.tar':  '',
                        '.xz':   'xz',
                        '.bz2':  'bz2',
                        '.tgz':  'gz',
                        '.gz':   'gz'}
    ARCHS = {'x86_64': '64', 'i386': '32'}
    DEFAULT_PROFILE = "default"
    CACHE_DELTA = timedelta(days=1)
    JSON_OUTPUT = "LEAF_JSON_OUTPUT"


class LeafFiles():
    '''
    Files & Folders used by Leaf
    '''
    WS_CONFIG_FILENAME = "leaf-workspace.json"
    WS_DATA_FOLDERNAME = "leaf-data"
    CURRENT_PROFILE = "current"
    USER_HOME = Path(os.path.expanduser("~"))
    DEFAULT_LEAF_ROOT = USER_HOME / 'leaf'
    DEFAULT_CONFIG_FILE = USER_HOME / '.leaf-config.json'
    CACHE_FOLDER = USER_HOME / '.cache' / 'leaf'
    FILES_CACHE_FOLDER = CACHE_FOLDER / "files"
    REMOTES_CACHE_FILE = CACHE_FOLDER / 'remotes.json'


class JsonConstants(object):
    '''
    Constants for Json grammar
    '''
    # Configuration
    CONFIG_REMOTES = 'remotes'
    CONFIG_ENV = 'env'
    CONFIG_ROOT = 'rootfolder'

    # Index
    REMOTE_NAME = 'name'
    REMOTE_DATE = 'date'
    REMOTE_DESCRIPTION = 'description'
    REMOTE_COMPOSITE = 'composite'
    REMOTE_PACKAGES = 'packages'
    REMOTE_PACKAGE_SIZE = 'size'
    REMOTE_PACKAGE_FILE = 'file'
    REMOTE_PACKAGE_SHA1SUM = 'sha1sum'

    # Manifest
    INFO = 'info'
    INFO_NAME = 'name'
    INFO_VERSION = 'version'
    INFO_LEAF_MINVER = 'leafMinVersion'
    INFO_DEPENDS = 'depends'
    INFO_REQUIRES = 'requires'
    INFO_MASTER = 'master'
    INFO_DESCRIPTION = 'description'
    INSTALL = 'install'
    UNINSTALL = 'uninstall'
    STEP_TYPE = 'type'
    STEP_LABEL = 'label'
    STEP_IGNORE_FAIL = 'ignoreFail'
    STEP_EXEC = 'exec'
    STEP_EXEC_ENV = 'env'
    STEP_EXEC_COMMAND = 'command'
    STEP_EXEC_VERBOSE = 'verbose'
    STEP_LINK = 'link'
    STEP_LINK_NAME = 'name'
    STEP_LINK_TARGET = 'target'
    STEP_COPY = 'copy'
    STEP_COPY_SOURCE = 'source'
    STEP_COPY_DESTINATION = 'destination'
    STEP_DELETE = 'delete'
    STEP_DELETE_FILES = 'files'
    STEP_DOWNLOAD = 'download'
    STEP_DOWNLOAD_URL = 'url'
    STEP_DOWNLOAD_RELATIVEURL = 'relativeUrl'
    STEP_DOWNLOAD_FILENAME = 'filename'
    STEP_DOWNLOAD_SHA1SUM = REMOTE_PACKAGE_SHA1SUM
    ENV = 'env'

    # Extra
    INFO_SUPPORTEDMODULES = 'supportedModules'

    # Profiles
    WS_PROFILES = "profiles"
    WS_LEAFMINVERSION = "leafMinVersion"
    WS_ENV = "env"
    WS_REMOTES = "remotes"
    WS_PROFILE_PACKAGES = "packages"
    WS_PROFILE_ENV = "env"

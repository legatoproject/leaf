'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import os
from pathlib import Path
import platform


class LeafConstants():
    '''
    Constants needed by Leaf
    '''
    MIN_PYTHON_VERSION = (3, 4)
    MANIFEST = 'manifest.json'
    VAR_PREFIX = '@'
    DOWNLOAD_TIMEOUT = 5
    LEAF_COMPRESSION = {'.leaf': 'xz',
                        '.tar':  '',
                        '.xz':   'xz',
                        '.bz2':  'bz2',
                        '.tgz':  'gz',
                        '.gz':   'gz'}
    ARCHS = {'x86_64': '64', 'i386': '32'}
    CURRENT_OS = platform.system().lower() + ARCHS.get(platform.machine(), "")


class LeafFiles():
    '''
    Files & Folders used by Leaf
    '''
    USER_HOME = Path(os.path.expanduser("~"))
    DEFAULT_LEAF_ROOT = USER_HOME / 'legato' / 'packages'
    DEFAULT_CONFIG_FILE = USER_HOME / '.leaf-config.json'
    CACHE_FOLDER = USER_HOME / '.cache' / 'leaf'
    FILES_CACHE_FOLDER = CACHE_FOLDER / "files"
    REMOTES_CACHE_FILE = CACHE_FOLDER / 'remotes.json'
    LICENSES_CACHE_FILE = CACHE_FOLDER / 'licenses.json'


class JsonConstants(object):
    '''
    Constants for Json grammar
    '''
    # Configuration
    CONFIG_REMOTES = 'remotes'
    CONFIG_ENV = 'env'
    CONFIG_ROOT = 'rootfolder'
    CONFIG_VARIABLES = 'variables'

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
    INFO_DEPENDS = 'depends'
    INFO_DEPENDS_LEAF = 'leaf'
    INFO_DEPENDS_DEB = 'deb'
    INFO_MASTER = 'master'
    INFO_DESCRIPTION = 'description'
    INFO_LICENSES = 'licenses'
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
    INFO_SUPPORTEDOS = 'supportedOs'

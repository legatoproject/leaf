"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import os
from datetime import timedelta
from pathlib import Path

from leaf.core.settings import EnvVar, LeafSetting, RegexValidator, StaticSettings


class CommonSettings(StaticSettings):
    PWD = EnvVar("PWD")
    WORKSPACE = EnvVar("LEAF_WORKSPACE")
    CONFIG_FOLDER = EnvVar("LEAF_CONFIG", default="~/.config/leaf")
    VERBOSITY = EnvVar("LEAF_VERBOSE", validator=RegexValidator("(default|verbose|quiet)"))


class LeafSettings(CommonSettings):

    INSTALL_FOLDER = LeafSetting("leaf.root", "LEAF_ROOT", description="Folder where leaf packages are installed", default="~/.leaf")
    CACHE_FOLDER = LeafSetting("leaf.cache", "LEAF_CACHE", description="Leaf cache", default="~/.cache/leaf")
    RESOURCES_FOLDER = LeafSetting("leaf.resources", "LEAF_RESOURCES", description="Leaf resources folder")

    DEBUG_MODE = LeafSetting("leaf.debug", "LEAF_DEBUG", description="Enable traces")
    NON_INTERACTIVE = LeafSetting("leaf.noninteractive", "LEAF_NON_INTERACTIVE", description="Do not ask for confirmations, assume yes")
    DISABLE_LOCKS = LeafSetting("leaf.locks.disable", "LEAF_DISABLE_LOCKS", description="Disable lock files for install operations")
    NOPLUGIN = LeafSetting("leaf.plugins.disable", "LEAF_NOPLUGIN", description="Disable plugins")
    PAGER = LeafSetting("leaf.pager", "LEAF_PAGER", description="Force a pager when a pager is needed")

    DOWNLOAD_TIMEOUT = LeafSetting(
        "leaf.download.timeout", "LEAF_TIMEOUT", description="Timeout (in sec) for download operations", default=20, validator=RegexValidator("[0-9]+")
    )
    DOWNLOAD_RETRY = LeafSetting(
        "leaf.download.retry", "LEAF_RETRY", description="Retry count for download operations", default=5, validator=RegexValidator("[0-9]+")
    )
    DOWNLOAD_NORESUME = LeafSetting("leaf.download.resume.disable", "LEAF_NORESUME", description="Disable resume when a download fails")
    GPG_KEYSERVER = LeafSetting(
        "leaf.gpg.server", "LEAF_GPG_KEYSERVER", description="Server where GPG keys will be fetched", default="subset.pool.sks-keyservers.net"
    )
    CUSTOM_TAR = LeafSetting("leaf.build.tar", "LEAF_CUSTOM_TAR", description="Use custom tar binary instead of *tar* command when generating artifacts")
    CUSTOM_THEME = LeafSetting("leaf.theme", "LEAF_THEME", description="Custom color theme")


class LeafConstants:

    """
    Constants needed by Leaf
    """

    DEFAULT_ERROR_RC = 2
    MIN_PYTHON_VERSION = (3, 4)
    COLORAMA_MIN_VERSION = "0.3.3"
    DEFAULT_PROFILE = "default"
    CACHE_DELTA = timedelta(days=1)
    CACHE_SIZE_MAX = 5 * 1024 * 1024 * 1024  # 5GB
    GPG_SIG_EXTENSION = ".asc"
    LATEST = "latest"
    DEFAULT_PAGER = pager = ("less", "-R", "-S", "-P", "Leaf -- Press q to exit")
    DEFAULT_SHELL = "bash"


class LeafFiles:

    """
    Files & Folders used by Leaf
    """

    MANIFEST = "manifest.json"
    # Workspace
    WS_CONFIG_FILENAME = "leaf-workspace.json"
    WS_DATA_FOLDERNAME = "leaf-data"
    CURRENT_PROFILE_LINKNAME = "current"
    # Configuration folders
    ETC_PREFIX = Path("/etc/leaf")
    USER_RESOURCE_FOLDER = Path(os.path.expanduser("~/.local/share/leaf"))
    SYSTEM_RESOURCE_FOLDER = Path("/usr/share/leaf")
    # Configuration files
    CONFIG_FILENAME = "config.json"
    CACHE_DOWNLOAD_FOLDERNAME = "files"
    CACHE_REMOTES_FILENAME = "remotes.json"
    THEMES_FILENAME = "themes.ini"
    PLUGINS_DIRNAME = "plugins"
    GPG_DIRNAME = "gpg"
    LOCK_FILENAME = "lock"
    # Releng
    EXTINFO_EXTENSION = ".info"

    @staticmethod
    def find_leaf_resource(name: str = None):
        folder = None
        if LeafSettings.RESOURCES_FOLDER.is_set():
            folder = Path(LeafSettings.RESOURCES_FOLDER.value)
        elif LeafFiles.USER_RESOURCE_FOLDER.is_dir():
            folder = LeafFiles.USER_RESOURCE_FOLDER
        else:
            folder = LeafFiles.SYSTEM_RESOURCE_FOLDER

        if folder.is_dir():
            out = folder if name is None else folder / name
            if out.exists():
                return out


class JsonConstants(object):

    """
    Constants for Json grammar
    """

    # Configuration
    CONFIG_REMOTES = "remotes"
    CONFIG_REMOTE_URL = "url"
    CONFIG_REMOTE_ENABLED = "enabled"
    CONFIG_REMOTE_GPGKEY = "gpgKey"
    CONFIG_ENV = "env"

    # Index
    REMOTE_NAME = "name"
    REMOTE_DATE = "date"
    REMOTE_DESCRIPTION = "description"
    REMOTE_PACKAGES = "packages"
    REMOTE_PACKAGE_SIZE = "size"
    REMOTE_PACKAGE_FILE = "file"
    REMOTE_PACKAGE_HASH = "hash"

    # Manifest
    INFO = "info"
    INFO_NAME = "name"
    INFO_VERSION = "version"
    INFO_DATE = "date"
    INFO_LEAF_MINVER = "leafMinVersion"
    INFO_FINALSIZE = "finalSize"
    INFO_DEPENDS = "depends"
    INFO_REQUIRES = "requires"
    INFO_MASTER = "master"
    INFO_DESCRIPTION = "description"
    INFO_TAGS = "tags"
    INFO_AUTOUPGRADE = "upgrade"
    INSTALL = "install"
    SYNC = "sync"
    UNINSTALL = "uninstall"
    STEP_LABEL = "label"
    STEP_IGNORE_FAIL = "ignoreFail"
    STEP_EXEC_ENV = "env"
    STEP_EXEC_COMMAND = "command"
    STEP_EXEC_VERBOSE = "verbose"
    STEP_EXEC_SHELL = "shell"
    ENV = "env"
    ENTRYPOINTS = "bin"
    ENTRYPOINT_PATH = "path"
    ENTRYPOINT_DESCRIPTION = "description"
    ENTRYPOINT_SHELL = "shell"
    PLUGINS = "plugins"
    PLUGIN_PREFIX = "location"
    PLUGIN_DESCRIPTION = "description"
    PLUGIN_SOURCE = "source"
    PLUGIN_CLASS = "class"
    SETTINGS = "settings"
    SETTING_DESCRIPTION = "description"
    SETTING_KEY = "key"
    SETTING_REGEX = "regex"
    SETTING_SCOPES = "scopes"

    # Profiles
    WS_PROFILES = "profiles"
    WS_LEAFMINVERSION = "leafMinVersion"
    WS_ENV = "env"
    WS_REMOTES = "remotes"
    WS_PROFILE_PACKAGES = "packages"
    WS_PROFILE_ENV = "env"

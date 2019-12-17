"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import os
from pathlib import Path

from leaf.core.settings import EnvVar, LeafSetting, RegexValidator, StaticSettings


class CommonSettings(StaticSettings):
    PWD = EnvVar("PWD")
    WORKSPACE = EnvVar("LEAF_WORKSPACE")
    CONFIG_FOLDER = EnvVar("LEAF_CONFIG", default="~/.config/leaf")
    VERBOSITY = EnvVar("LEAF_VERBOSE", validator=RegexValidator("(default|verbose|quiet)"))
    SHELL = EnvVar("SHELL")


class LeafSettings(CommonSettings):

    USER_PKG_FOLDER = LeafSetting("leaf.user.root", "LEAF_USER_ROOT", description="Folder where leaf packages are installed", default="~/.leaf")
    SYSTEM_PKG_FOLDERS = LeafSetting(
        "leaf.system.roots",
        "LEAF_SYSTEM_ROOTS",
        description="Folders where system leaf packages are installed",
        default=os.pathsep.join(("/usr/share/leaf/packages", "/usr/local/share/leaf/packages", "~/.local/share/leaf/packages")),
    )
    CACHE_FOLDER = LeafSetting("leaf.cache", "LEAF_CACHE", description="Leaf cache", default="~/.cache/leaf")
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
    PROFILE_NORELATIVE = LeafSetting(
        "leaf.profile.relative.disable", "LEAF_PROFILE_NORELATIVE", description="Disable relative path for installed package of a profile"
    )
    DEFAULT_SHELL = LeafSetting(
        "leaf.shell.default", "LEAF_SHELL_DEFAULT", description="Shell used when leaf needs an internal shell to run commands", default="bash"
    )
    SMART_REFRESH_DELTA = LeafSetting(
        "leaf.remote.smartrefresh",
        "LEAF_REMOTE_SMARTREFRESH",
        description="Delta time (in days) before remotes are automatically fetched",
        default=1,
        validator=RegexValidator("[0-9]+"),
    )
    HELP_DEFAULT_FORMAT = LeafSetting("leaf.help.default.format", "LEAF_HELP_DEFAULT_FORMAT", description="Default format for help topics", default="man")
    HELP_DEFAULT_OPEN = LeafSetting(
        "leaf.help.default.open", "LEAF_HELP_DEFAULT_OPEN", description="Default command to open help topics if not 'manpage' format", default="xdg-open"
    )


class LeafConstants:

    """
    Constants needed by Leaf
    """

    DEFAULT_ERROR_RC = 2
    MIN_PYTHON_VERSION = (3, 5)
    COLORAMA_MIN_VERSION = "0.3.3"
    DEFAULT_PROFILE = "default"
    CACHE_SIZE_MAX = 5 * 1024 * 1024 * 1024  # 5GB
    GPG_SIG_EXTENSION = ".asc"
    EXTINFO_EXTENSION = ".info"
    LATEST = "latest"
    DEFAULT_PAGER = pager = ("less", "-R", "-S", "-P", "Leaf -- Press q to exit")


class LeafFiles:

    """
    Files & Folders used by Leaf
    """

    MANIFEST = "manifest.json"
    SCHEMA = "manifest.schema.json"
    # Workspace
    WS_CONFIG_FILENAME = "leaf-workspace.json"
    WS_DATA_FOLDERNAME = "leaf-data"
    CURRENT_PROFILE_LINKNAME = "current"
    # Configuration folders
    ETC_PREFIX = Path("/etc/leaf")
    # Configuration files
    CONFIG_FILENAME = "config.json"
    CACHE_DOWNLOAD_FOLDERNAME = "files"
    CACHE_REMOTES_FOLDERNAME = "remotes"
    THEMES_FILENAME = "themes.ini"
    PLUGINS_DIRNAME = "plugins"
    GPG_DIRNAME = "gpg"
    LOCK_FILENAME = "lock"


class JsonConstants(object):

    """
    Constants for Json grammar
    """

    LEAFMINVERSION = "leafMinVersion"

    # Configuration
    CONFIG_REMOTES = "remotes"
    CONFIG_REMOTE_URL = "url"
    CONFIG_REMOTE_PRIORITY = "priority"
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
    INFO_LEAF_MINVER = LEAFMINVERSION
    INFO_FINALSIZE = "finalSize"
    INFO_DEPENDS = "depends"
    INFO_REQUIRES = "requires"
    INFO_MASTER = "master"
    INFO_DESCRIPTION = "description"
    INFO_DOCUMENTATION = "documentation"
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
    ENV = "env"
    ENVIN = "env.activate"
    ENVOUT = "env.deactivate"
    ENTRYPOINTS = "bin"
    ENTRYPOINT_PATH = "path"
    ENTRYPOINT_DESCRIPTION = "description"
    PLUGINS = "plugins"
    PLUGIN_DESCRIPTION = "description"
    PLUGIN_SOURCE = "source"
    PLUGIN_CLASS = "class"
    SETTINGS = "settings"
    SETTING_DESCRIPTION = "description"
    SETTING_KEY = "key"
    SETTING_REGEX = "regex"
    SETTING_SCOPES = "scopes"
    HELPTOPICS = "help"

    # Profiles
    WS_PROFILES = "profiles"
    WS_ENV = "env"
    WS_REMOTES = "remotes"
    WS_PROFILE_PACKAGES = "packages"
    WS_PROFILE_ENV = "env"

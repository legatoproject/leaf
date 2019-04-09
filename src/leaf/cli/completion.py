"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.api import ConfigurationManager, PackageManager, RemoteManager, WorkspaceManager
from leaf.model.tags import TagUtils


def complete_environment_variable(*args, **kwargs):
    if kwargs["parser"].prog == "leaf env user":
        return ConfigurationManager().read_user_configuration().build_environment().keys()
    elif kwargs["parser"].prog == "leaf env workspace":
        wm = WorkspaceManager(WorkspaceManager.find_root())
        if wm.is_initialized:
            return wm.read_ws_configuration().build_environment().keys()
    elif kwargs["parser"].prog == "leaf env profile":
        wm = WorkspaceManager(WorkspaceManager.find_root())
        if wm.is_initialized:
            return wm.get_current_profile().build_environment().keys()


def complete_all_packages(*args, **kwargs):
    return complete_available_packages(*args, **kwargs) + complete_installed_packages(*args, **kwargs)


def complete_available_packages(*args, **kwargs):
    return list(map(str, PackageManager().list_available_packages().keys()))


def complete_installed_packages(*args, **kwargs):
    return list(map(str, PackageManager().list_installed_packages().keys()))


def complete_installed_packages_tags(*args, **kwargs):
    out = {TagUtils.LATEST}
    for ip in PackageManager().list_installed_packages().values():
        out.update(set(ip.all_tags))
    return out


def complete_available_packages_tags(*args, **kwargs):
    out = {TagUtils.LATEST, TagUtils.INSTALLED}
    for ip in PackageManager().list_available_packages().values():
        out.update(set(ip.all_tags))
    return out


def complete_remotes(*args, **kwargs):
    return RemoteManager().list_remotes().keys()


def complete_settings(*args, **kwargs):
    return ConfigurationManager().get_settings().keys()


def complete_profiles(*args, **kwargs):
    wm = WorkspaceManager(WorkspaceManager.find_root())
    if wm.is_initialized:
        return wm.list_profiles().keys()


def complete_binaries(*args, **kwargs):
    out = []
    for ip in PackageManager().list_installed_packages().values():
        for e in ip.binaries.values():
            out.append(e.name)
    return out

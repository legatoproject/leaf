"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import os
from argparse import ONE_OR_MORE, Action, Namespace
from builtins import ValueError
from pathlib import Path

from leaf.cli.completion import complete_available_packages, complete_environment_variable, complete_installed_packages
from leaf.model.base import Scope


def get_optional_arg(args: Namespace, name: str, default=None):
    out = vars(args).get(name)
    return default if out is None else out


def string_to_bool(value: str):
    if value.strip().lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif value.strip().lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ValueError("Boolean value expected.")


class EnvSetterAction(Action):
    def __init__(self, *args, **kwargs):
        if "nargs" not in kwargs:
            kwargs["nargs"] = 0
        Action.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        value = None
        if self.nargs == 0:
            if self.const is None:
                raise ValueError()
            value = self.const
        elif self.nargs == 1:
            if values[0] is None:
                raise ValueError()
            value = values[0]
        elif self.nargs == ONE_OR_MORE:
            if values[0] is None:
                raise ValueError()
            separator = self.const if self.const is not None else ":"
            if self.dest in os.environ.keys() and len(os.environ[self.dest]) > 0:
                value = os.environ[self.dest] + separator + values[0]
            else:
                value = values[0]
        else:
            raise ValueError()
        if value is None:
            raise ValueError("Cannot set null value for {dest}".format(dest=self.dest))
        os.environ[self.dest] = str(value)


def init_common_args(parser, add_rm_env=False, env_scripts=False, add_rm_packages=False, with_scope=False):
    if add_rm_env:
        parser.add_argument("--set", dest="env_add_list", action="append", metavar="KEY=VALUE", help="add given environment variable")
        parser.add_argument(
            "--unset", dest="env_rm_list", action="append", metavar="KEY", help="remote given environment variable"
        ).completer = complete_environment_variable
    if env_scripts:
        parser.add_argument("--activate-script", dest="activate_script", metavar="FILE", type=Path, help="create a script to activate the env variables")
        parser.add_argument("--deactivate-script", dest="deactivate_script", metavar="FILE", type=Path, help="create a script to deactivate the env variables")
    if add_rm_packages:
        parser.add_argument(
            "-p", "--add-package", dest="pkg_add_list", action="append", metavar="PKGNAME", help="add given package"
        ).completer = complete_available_packages
        parser.add_argument(
            "--rm-package", dest="pkg_rm_list", action="append", metavar="PKGNAME", help="remove given package"
        ).completer = complete_installed_packages
    if with_scope:
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-U", "--user", dest="env_scope", action="store_const", const=Scope.USER, help="use user configuration environment")
        group.add_argument("-W", "--workspace", dest="env_scope", action="store_const", const=Scope.WORKSPACE, help="use workspace environment")
        group.add_argument("-P", "--profile", dest="env_scope", action="store_const", const=Scope.PROFILE, help="use profile environment")

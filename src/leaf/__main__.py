"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import sys
from signal import SIGINT, signal

from leaf.api import ConfigurationManager, LoggerManager
from leaf.cli.commands import LeafRootCommand
from leaf.cli.plugins import LeafPluginManager
from leaf.core.constants import LeafConstants, LeafSettings
from leaf.core.error import LeafException, UserCancelException
from leaf.core.utils import check_supported_python_version


def main():
    sys.exit(run_leaf(sys.argv[1:]))


def run_leaf(argv, catch_int_sig=True):
    # Check supported python
    check_supported_python_version()

    # Catch CTRL-C
    if catch_int_sig:

        def signal_handler(sig, frame):
            raise UserCancelException()

        signal(SIGINT, signal_handler)

    out = None
    try:
        # Init leaf configuration
        cm = ConfigurationManager()
        cm.init_leaf_settings()
        # Plugin manager
        pm = None
        if not LeafSettings.NOPLUGIN.as_boolean():
            pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        # Setup the app CLI parser
        parser = LeafRootCommand(pm).setup(None)
        # Try to enable argcomplete library
        try:
            import argcomplete

            argcomplete.autocomplete(parser)
        except ImportError:
            pass

        # Parse args
        args, uargs = parser.parse_known_args(argv)
        # Execute command handler
        out = args.handler.safe_execute(args, uargs)
    except Exception as e:
        LoggerManager().print_exception(e)
        out = e.exit_code if isinstance(e, LeafException) else LeafConstants.DEFAULT_ERROR_RC
    return out if out is not None else 0


if __name__ == "__main__":
    main()

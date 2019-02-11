'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import sys
from signal import SIGINT, signal

from leaf.api import ConfigurationManager
from leaf.cli.leaf import LeafRootCommand
from leaf.cli.plugins import LeafPluginManager
from leaf.core.constants import LeafFiles, LeafSettings
from leaf.core.error import UserCancelException


def main():
    return runLeaf(sys.argv[1:])


def runLeaf(argv, catchInt=True):
    # Catch CTRL-C
    if catchInt:
        def signal_handler(sig, frame):
            raise UserCancelException()
        signal(SIGINT, signal_handler)
    # Init leaf configuration
    cm = ConfigurationManager()
    cm.initLeafSettings()
    # Plugin manager
    pm = LeafPluginManager()
    if not LeafSettings.NOPLUGIN.as_boolean():
        pm.loadBuiltinPlugins(LeafFiles.getResource(
            LeafFiles.PLUGINS_DIRNAME, check_exists=False))
        pm.loadUserPlugins(cm.readConfiguration().getRootFolder())
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
    return args.handler.safeExecute(args, uargs)


if __name__ == '__main__':
    main()

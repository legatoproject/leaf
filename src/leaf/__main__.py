'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import os
import sys
from signal import SIGINT, signal

from leaf.cli.leaf import LeafRootCommand
from leaf.constants import EnvConstants
from leaf.core.error import UserCancelException


def main():
    return runLeaf(sys.argv[1:])


def runLeaf(argv, catchInt=True):
    # Catch CTRL-C
    if catchInt:
        def signal_handler(sig, frame):
            raise UserCancelException()
        signal(SIGINT, signal_handler)
    # Setup the app CLI parser
    parser = LeafRootCommand().setup(None)
    # Try to enable argcomplete library
    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    # Parse args
    args, uargs = parser.parse_known_args(argv)
    # Init some env vars overriden by arguments
    if args.workspace is not None:
        os.environ[EnvConstants.WORKSPACE_ROOT] = str(args.workspace)
    if args.nonInteractive:
        os.environ[EnvConstants.NON_INTERACTIVE] = "1"
    # Execute command handler
    return args.handler.safeExecute(args, uargs)


if __name__ == '__main__':
    main()

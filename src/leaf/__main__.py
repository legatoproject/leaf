'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cli import LeafCli
import sys


def main():
    return LeafCli().run(sys.argv[1:])


if __name__ == '__main__':
    main()

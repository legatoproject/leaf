'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
import os
import re
import subprocess
from pathlib import Path

from leaf.cli.plugins import LeafPluginCommand
from leaf.core.constants import LeafSettings
from leaf.core.error import LeafException


class HelpPlugin(LeafPluginCommand):

    def _configureParser(self, parser):
        parser.add_argument('-l', '--list',
                            dest='list_topics',
                            action='store_true',
                            help="list all available topics")
        parser.add_argument('topic',
                            nargs=argparse.OPTIONAL,
                            metavar='TOPIC',
                            help='the profile name')

    def getManpage(self, page):
        rc, out = subprocess.getstatusoutput("man -w " + page)
        if rc == 0:
            return out

    def execute(self, args, uargs):
        if args.list_topics:
            # List all topics
            leafManpage = self.getManpage('leaf')
            manpageDir = Path(leafManpage).parent
            leafManpagePattern = re.compile("leaf-(.*)\\.[0-9]")
            for manpage in sorted(manpageDir.iterdir()):
                if manpage.is_file():
                    m = leafManpagePattern.fullmatch(manpage.name)
                    if m is not None:
                        print(m.group(1))
        else:
            manpage = "leaf"
            if args.topic is not None:
                manpage += "-" + args.topic
            if self.getManpage(manpage) is None:
                raise LeafException(
                    "No leaf help page found for " + args.topic,
                    hints="Use 'leaf help --list' to see all topics",
                    exitCode=3)
            manCommand = ["man"]
            if LeafSettings.NON_INTERACTIVE.as_boolean():
                manCommand += ["-P", "cat"]
            manCommand.append(manpage)
            os.execv(subprocess.getoutput("which man"), manCommand)

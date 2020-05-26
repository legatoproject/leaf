"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import argparse
import subprocess

from leaf.cli.base import LeafCommand
from leaf.cli.completion import complete_help
from leaf.core.constants import LeafSettings
from leaf.core.error import LeafException
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.modelutils import keep_latest_mf
from leaf.model.package import PackageIdentifier
from leaf.model.steps import VariableResolver
from leaf.rendering.renderer.helptopic import HelpTopicListRenderer


class HelpCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "help", "read leaf documentation")

    def _get_examples(self):
        return [
            ("leaf help", "list all help topics"),
            ("leaf help <TOPIC>", "open the *topic* documentation man page"),
            ("leaf help --format html <TOPIC>", "open the HTML *topic* documentation in the default web browser"),
        ]

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-p", "--package", dest="package", metavar="PKG_IDENTIFIER", type=PackageIdentifier.parse, help="use help from specified package")
        parser.add_argument("-f", "--format", help="choose documentation format")
        parser.add_argument("topic", metavar="TOPIC", nargs=argparse.OPTIONAL, help="name of the documentation topic").completer = complete_help

    def get_topics(self, iplist: list) -> dict:
        out = []
        for ip in iplist:
            out += ip.help_topics.values()
        return out

    def find_topic(self, topics: list, name: str):
        # Exact match
        for t in topics:
            if name == t.full_name:
                return t
        # Partial match
        matching_topics = [t for t in topics if t.name == name]
        if len(matching_topics) == 0:
            # No partial matches found
            # Add default "leaf-" prefix to search name and try again
            matching_topics = [t for t in topics if t.name == ("leaf-" + name)]
            if len(matching_topics) == 1:
                return matching_topics[0]
            raise LeafException("Cannot find topic: {0}".format(name), hints="Use 'leaf help' to list all available topics")
        if len(matching_topics) > 1:
            raise LeafException("Ambiguous topic name: {0}".format(name), hints=["You can use 'leaf help {t.full_name}'".format(t=t) for t in matching_topics])
        return matching_topics[0]

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)

        ipmap = wm.list_installed_packages()
        searching_iplist = None

        if args.package is not None:
            # User forces the package
            searching_iplist = DependencyUtils.installed(
                [args.package], ipmap, env=Environment.build(wm.build_builtin_environment(), wm.build_user_environment())
            )
        else:
            # Use installed packages
            searching_iplist = keep_latest_mf(ipmap.values())

        topics = self.get_topics(searching_iplist)
        if args.topic is not None:
            topic = self.find_topic(topics, args.topic)
            fmt = args.format
            if fmt is None:
                # No format given
                if LeafSettings.HELP_DEFAULT_FORMAT.value in topic.resources.keys():
                    # Default format is available
                    fmt = LeafSettings.HELP_DEFAULT_FORMAT.value
                elif len(topic.resources.keys()) == 1:
                    # Only one format available
                    fmt = next(iter(topic.resources.keys()))

            if fmt is None or fmt not in topic.resources.keys():
                # Ensure that this topic is available for needed format
                raise LeafException(
                    "You need to specify a format for topic '{topic}'".format(topic=args.topic),
                    hints=["For example 'leaf help --format {fmt} {topic}'".format(fmt=fmt, topic=args.topic) for fmt in topic.resources.keys()],
                )

            # Resolve resource path since it can contain @{} variables
            resource = VariableResolver(topic.installed_package, ipmap.values()).resolve(topic.resources[fmt])
            if fmt == "man":
                # If format is 'man', use manpage reader
                command = ["man", "-P", "cat"] if LeafSettings.NON_INTERACTIVE.as_boolean() else ["man"]
                command.append(resource)
                subprocess.check_call(command)
            else:
                # Use default resource handler
                subprocess.check_call([LeafSettings.HELP_DEFAULT_OPEN.value, resource])
        else:
            # Print mode
            scope = "installed packages"
            if args.package is not None:
                scope = args.package
            rend = HelpTopicListRenderer(scope, filter_format=args.format)
            rend.extend(searching_iplist)
            wm.print_renderer(rend)

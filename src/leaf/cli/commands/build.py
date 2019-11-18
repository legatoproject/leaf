"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import argparse
from builtins import ValueError
from pathlib import Path

from leaf.api import RelengManager
from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import string_to_bool
from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.error import LeafException


class BuildPackSubCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "pack", "build a package")

    def _get_examples(self):
        return [
            ("leaf build pack -i path/to/packageFolder/ -o package.leaf -- -z .", "Build an GZIP compressed archive"),
            (
                "leaf build pack -i path/to/packageFolder/ -o package.leaf -- -v -J -X /tmp/exclude.list .",
                "Build an XZ compressed archive with some files excluded (from /tmp/exclude.list), tar will be verbose",
            ),
            (
                "leaf build pack -i path/to/packageFolder/ -o package.leaf -- -J manifest.json",
                "Build an XZ compressed archive containing only the manifest.json file",
            ),
        ]

    def _get_epilog_text(self):
        out = "notes: \n"
        out += "  - extra tar options must begin with a '--'\n"
        out += "  - if you specify extra tar options, you must specify the content to include (usually, end your command with a '.')\n"
        out += "\n" + super()._get_epilog_text()
        return out

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-o", "--output", metavar="FILE", required=True, type=Path, dest="output_file", help="output file")
        parser.add_argument("-i", "--input", metavar="FOLDER", type=Path, dest="input_folder", help="package folder")
        parser.add_argument("--no-info", action="store_false", dest="syore_external_info", help="do not store artifact info in a separate file")
        parser.add_argument("--validate-only", action="store_true", dest="validate_only", help="only validate manifest.json model, do not create the package")
        parser.add_argument("tar_extra_args", metavar="TAR_ARGS", nargs="*", help="extra arguments given to tar command line\n(must start with '--')")

    def execute(self, args, uargs):
        rm = RelengManager()

        pkg_folder = None
        if args.input_folder is None:
            pkg_folder = Path(".")
        elif args.input_folder.is_dir():
            pkg_folder = args.input_folder
        elif args.input_folder.is_file() and args.input_folder.name == LeafFiles.MANIFEST:
            # Handles legacy, arg is not the folder but the manifest
            pkg_folder = args.input_folder.parent
        else:
            raise ValueError("Invalid input folder")

        rm.create_package(
            pkg_folder, args.output_file, store_extenal_info=args.syore_external_info, tar_extra_args=args.tar_extra_args, validate_only=args.validate_only
        )


class BuildIndexSubCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "index", "build a repository index.json")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-o", "--output", required=True, metavar="FILE", type=Path, dest="output_file", help="the new json index file")
        parser.add_argument("-i", "--input", metavar="FILE", action="append", type=Path, dest="input_files", help="file containing list of artifacts path")
        parser.add_argument("--name", metavar="NAME", dest="index_name", help="name of the repository")
        parser.add_argument("--description", metavar="STRING", dest="index_description", help="description of the repository")
        parser.add_argument(
            "--no-info", action="store_false", dest="use_external_info", help="do not use info files (*.info), THIS MAY SLOW THE INDEX GENERATION"
        )
        parser.add_argument("--no-extra-tags", action="store_false", dest="use_extra_tags", help='do not use extra tags in "*.tags" files')
        parser.add_argument("--prettyprint", action="store_true", dest="prettyprint", help="pretty print json")
        parser.add_argument(
            "--resolve", action="store_true", dest="resolve", help="Resolves artifacts path to ensure they are relative to index (NB: symlinks are resolved)"
        )
        parser.add_argument("artifacts", type=Path, nargs=argparse.REMAINDER, help="leaf artifacts")

    def execute(self, args, uargs):
        rm = RelengManager()
        artifacts = []
        artifacts += args.artifacts
        if args.input_files:
            for input_file in args.input_files:
                rm.logger.print_default("Using artifacts from {0}".format(input_file))
                with input_file.open() as fp:
                    for line in filter(lambda l: l and not l.startswith("#"), map(str.strip, fp.read().splitlines())):
                        artifacts.append(Path(line))
        rm.generate_index(
            args.output_file,
            artifacts,
            name=args.index_name,
            description=args.index_description,
            use_external_info=args.use_external_info,
            use_extra_tags=args.use_extra_tags,
            prettyprint=args.prettyprint,
            resolve=args.resolve,
        )


class BuildManifestSubCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "manifest", "build a package manifest.json")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-o", "--output", metavar="FOLDER", type=Path, dest="output_folder", help="folder where the manifest.json will be generated")
        parser.add_argument(
            "--append", metavar="JSON_FILE", action="append", type=Path, dest="fragment_files", help="json fragment that will be added to generated manifest"
        )
        parser.add_argument("--env", action="store_true", dest="resolve_envvars", help="use environment variables to perform string replacement")

        cg = parser.add_argument_group(title="Setup common attributes")
        cg.add_argument("--name", metavar="NAME", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_NAME, help="set the package name")
        cg.add_argument("--version", metavar="VERSION", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_VERSION, help="set the package version")
        cg.add_argument(
            "--description", metavar="DESCRIPTION", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_DESCRIPTION, help="set the package description"
        )
        cg.add_argument("--date", metavar="DATE", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_DATE, help="set the date")
        cg.add_argument(
            "--minver",
            metavar="MINIMUM_VERSION",
            dest=JsonConstants.INFO + "_" + JsonConstants.INFO_LEAF_MINVER,
            help="set leaf minimum version to use the package",
        )
        cg.add_argument(
            "--master",
            metavar="BOOLEAN",
            dest=JsonConstants.INFO + "_" + JsonConstants.INFO_MASTER,
            type=string_to_bool,
            help="set master package (true|false)",
        )
        cg.add_argument(
            "--upgradable",
            metavar="BOOLEAN",
            dest=JsonConstants.INFO + "_" + JsonConstants.INFO_AUTOUPGRADE,
            type=string_to_bool,
            help="set package as upgradable (true|false)",
        )
        cg.add_argument(
            "--requires", metavar="PKGID", action="append", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_REQUIRES, help="add a required package"
        )
        cg.add_argument(
            "--depends", metavar="PKGID", action="append", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_DEPENDS, help="add a dependency package"
        )
        cg.add_argument("--tag", metavar="TAG", action="append", dest=JsonConstants.INFO + "_" + JsonConstants.INFO_TAGS, help="add a tag")

    def execute(self, args, uargs):
        rm = RelengManager()

        # Guess output file
        output_file = Path(LeafFiles.MANIFEST)
        if args.output_folder is not None:
            if not args.output_folder.is_dir():
                raise LeafException("Invalid output folder: {folder}".format(folder=args.output_folder))
            output_file = args.output_folder / LeafFiles.MANIFEST

        # Build the info map
        info_map = {}
        for k, v in vars(args).items():
            if k.startswith(JsonConstants.INFO + "_"):
                info_map[k[(len(JsonConstants.INFO) + 1) :]] = v

        rm.generate_manifest(output_file, fragment_files=args.fragment_files, info_map=info_map, resolve_envvars=args.resolve_envvars)

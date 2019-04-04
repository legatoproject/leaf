"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import os
import re
import subprocess
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from leaf.api import LoggerManager
from leaf.core.constants import JsonConstants, LeafConstants, LeafFiles, LeafSettings
from leaf.core.error import LeafException
from leaf.core.jsonutils import jlayer_update, jloadfile, jtostring, jwritefile
from leaf.core.utils import hash_compute
from leaf.model.modelutils import is_latest_package
from leaf.model.package import AvailablePackage, ConditionalPackageIdentifier, LeafArtifact, Manifest, PackageIdentifier


class RelengManager(LoggerManager):
    __TAR_FORBIDDEN_ARGS = {
        "-A",
        "--catenate",
        "--concatenate",
        "-c",
        "--create",
        "-d",
        "--diff",
        "--compare",
        "--delete",
        "-r",
        "--append",
        "-t",
        "--list",
        "--test-label",
        "-u",
        "--update",
        "-x",
        "--extract",
        "--get",
        "-C",
        "--directory",
        "-f",
        "--file",
    }
    """
    Methods needed for releng, ie generate packages and maintain repository
    """

    def __init__(self):
        LoggerManager.__init__(self)

    def __get_date_now(self):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def find_external_info_file(self, artifact: LeafArtifact):
        return artifact.parent / (artifact.name + LeafFiles.EXTINFO_EXTENSION)

    def __build_pkg_node(self, tarfile: Path, manifest: Manifest = None):
        out = OrderedDict()
        if manifest is None:
            manifest = LeafArtifact(tarfile)
        out[JsonConstants.INFO] = manifest.info_node
        out[JsonConstants.REMOTE_PACKAGE_HASH] = hash_compute(tarfile)
        out[JsonConstants.REMOTE_PACKAGE_SIZE] = tarfile.stat().st_size
        return out

    def create_package(self, input_folder: Path, output_file: Path, store_extenal_info: bool = True, tar_extra_args: list = None):
        """
        Create a leaf artifact from given folder containing a manifest.json
        """
        mffile = input_folder / LeafFiles.MANIFEST
        infofile = self.find_external_info_file(output_file)

        if not mffile.exists():
            raise LeafException("Cannot find manifest: {file}".format(file=mffile))

        manifest = Manifest.parse(mffile)

        if is_latest_package(manifest.identifier):
            raise LeafException("Invalid version for manifest {mf} ({kw} is a reserved keyword)".format(mf=mffile, kw=LeafConstants.LATEST))

        self.logger.print_default("Found package {mf.identifier} in {folder}".format(mf=manifest, folder=input_folder))

        # Check if external info file exists
        if not store_extenal_info and infofile.exists():
            raise LeafException(
                "A previous info file ({file}) exists for your package".format(file=infofile),
                hints="You should remove it with 'rm {file}'".format(file=infofile),
            )

        self.__exec_tar(output_file, input_folder, extra_args=tar_extra_args)

        self.logger.print_default("Leaf package created: {file}".format(file=output_file))

        if store_extenal_info:
            self.logger.print_default("Write info to {file}".format(file=infofile))
            jwritefile(infofile, self.__build_pkg_node(output_file, manifest=manifest), pp=True)

    def generate_index(
        self,
        index_file: Path,
        artifacts: list,
        name: str = None,
        description: str = None,
        use_external_info: bool = True,
        use_extra_tags: bool = True,
        prettyprint: bool = False,
    ):
        """
        Create an index.json referencing all given artifacts
        """

        # Create the "info" node
        info_node = OrderedDict()
        if name is not None:
            info_node[JsonConstants.REMOTE_NAME] = name
        if description is not None:
            info_node[JsonConstants.REMOTE_DESCRIPTION] = description
        info_node[JsonConstants.REMOTE_DATE] = self.__get_date_now()

        # Iterate over all artifacts
        packages_map = OrderedDict()
        for artifact in artifacts:
            artifact_node = None

            if use_external_info:
                infofile = self.find_external_info_file(artifact)
                if infofile.exists():
                    self.logger.print_default("Reading info from {file}".format(file=infofile))
                    artifact_node = jloadfile(infofile)

            if artifact_node is None:
                self.logger.print_default("Compute info for {artifact}".format(artifact=artifact))
                artifact_node = self.__build_pkg_node(artifact)

            ap = AvailablePackage(artifact_node, None)
            pi = ap.identifier
            if is_latest_package(pi):
                raise LeafException(
                    "Invalid version for package {artifact} ({word} is a reserved keyword)".format(artifact=artifact, word=LeafConstants.LATEST)
                )

            if pi in packages_map:
                self.logger.print_default("Artifact already present: {pi}".format(pi=pi))
                if ap.hashsum != AvailablePackage(packages_map[pi], None).hashsum:
                    raise LeafException("Artifact {pi} has multiple different artifacts for same version".format(pi=pi))
            else:
                # Read extra tags
                extratags_file = artifact.parent / (artifact.name + ".tags")
                if use_extra_tags and extratags_file.exists():
                    with extratags_file.open("r") as fp:
                        for tag in filter(None, map(str.strip, fp.read().splitlines())):
                            if tag not in ap.tags:
                                self.logger.print_default("Add extra tag {tag}".format(tag=tag))
                                ap.tags.append(tag)

                self.logger.print_default("Add package {pi}".format(pi=pi))
                relative_path = Path(artifact).relative_to(index_file.parent)
                artifact_node[JsonConstants.REMOTE_PACKAGE_FILE] = str(relative_path)
                packages_map[pi] = artifact_node

        # Create the json structure
        root_node = OrderedDict()
        root_node[JsonConstants.INFO] = info_node
        root_node[JsonConstants.REMOTE_PACKAGES] = list(packages_map.values())

        jwritefile(index_file, root_node, pp=prettyprint)
        self.logger.print_default("Index created: {index}".format(index=index_file))

    def generate_manifest(self, output_file: Path, fragment_files: list = None, info_map: dict = None, resolve_envvars: bool = False):
        """
        Used to create a manifest.json file
        """
        model = OrderedDict()

        # Load fragments
        if fragment_files is not None:
            for fragment_file in fragment_files:
                self.logger.print_default("Use json fragment: {fragment}".format(fragment=fragment_file))
                jlayer_update(model, jloadfile(fragment_file), list_append=True)

        # Load model
        manifest = Manifest(model)
        info = manifest.jsonget(JsonConstants.INFO, default=OrderedDict())

        # Set the common info
        if info_map is not None:
            for key in (
                JsonConstants.INFO_NAME,
                JsonConstants.INFO_VERSION,
                JsonConstants.INFO_DESCRIPTION,
                JsonConstants.INFO_MASTER,
                JsonConstants.INFO_DATE,
                JsonConstants.INFO_REQUIRES,
                JsonConstants.INFO_DEPENDS,
                JsonConstants.INFO_TAGS,
                JsonConstants.INFO_LEAF_MINVER,
                JsonConstants.INFO_AUTOUPGRADE,
            ):
                if key in info_map:
                    value = info_map[key]
                    if value is not None:
                        if key in (JsonConstants.INFO_REQUIRES, JsonConstants.INFO_DEPENDS, JsonConstants.INFO_TAGS):
                            # Handle lists
                            model_list = manifest.jsonpath([JsonConstants.INFO, key], default=[])
                            for motif in value:
                                if motif not in model_list:
                                    if key == JsonConstants.INFO_DEPENDS:
                                        # Try to parse as a conditional package
                                        # identifier
                                        ConditionalPackageIdentifier.parse(motif)
                                    elif key == JsonConstants.INFO_REQUIRES:
                                        # Try to parse as a package identifier
                                        PackageIdentifier.parse(motif)

                                    self.logger.print_verbose("Add '{motif}' to '{key}' list".format(motif=motif, key=key))
                                    model_list.append(motif)
                        else:
                            self.logger.print_verbose("Set '{key}' = '{value}'".format(key=key, value=value))
                            info[key] = value

        # String replacement
        jsonstr = jtostring(manifest.json, pp=True)
        if resolve_envvars:
            for var in set(re.compile(r"#\{([a-zA-Z0-9_]+)\}").findall(jsonstr)):
                value = os.environ.get(var)
                if value is None:
                    raise LeafException("Cannot find '{var}' in env".format(var=var), hints="Set the variable with 'export {var}=xxx'".format(var=var))
                self.logger.print_default("Replace {key} --> {value}".format(key=var, value=value))
                jsonstr = jsonstr.replace("#{{{var}}}".format(var=var), value)

        if is_latest_package(manifest.identifier):
            raise LeafException("Invalid version ({word} is a reserved keyword)".format(word=LeafConstants.LATEST))

        self.logger.print_default("Save '{mf.identifier}' manifest to {file}".format(mf=manifest, file=output_file))

        with output_file.open("w") as fp:
            fp.write(jsonstr)

    def __exec_tar(self, output: Path, workdir: Path, extra_args: list = None):
        tar = "tar"
        if LeafSettings.CUSTOM_TAR.is_set():
            tar = LeafSettings.CUSTOM_TAR.value
        command = [tar, "-c"]
        command += ["-f", output]
        command += ["-C", workdir]

        if extra_args is not None and len(extra_args) > 0:
            forbidden_args = set(extra_args) & RelengManager.__TAR_FORBIDDEN_ARGS
            if len(forbidden_args) > 0:
                raise LeafException("You should not use tar extra arguments: {invalid_args}".format(invalid_args=" ".join(forbidden_args)))
            command += extra_args
        else:
            command.append(".")

        command_text = " ".join(map(str, command))
        self.logger.print_default("Executing command: {cmd}".format(cmd=command_text))
        rc = subprocess.call(list(map(str, command)), stdout=None, stderr=subprocess.STDOUT)
        if rc != 0:
            raise LeafException("Error executing: {cmd}".format(cmd=command_text))

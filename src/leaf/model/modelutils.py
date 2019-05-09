import subprocess
from builtins import sorted

from leaf.core.constants import LeafConstants, LeafSettings
from leaf.core.utils import CURRENT_LEAF_VERSION
from leaf.core.error import InvalidPackageNameException
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier


def check_leaf_min_version(mflist: list):
    out = None
    for mf in mflist:
        mf_min_version = mf.leaf_min_version
        if mf_min_version is not None and mf_min_version > CURRENT_LEAF_VERSION:
            # package not supported
            if out is None or mf_min_version > out:
                out = mf_min_version
    return out


def build_shell_command(*args, env=None):
    # In shell mode, env is evaluated in the command line
    exports = []
    if isinstance(env, dict):
        for k, v in env.items():
            exports.append(Environment.tostring_export(k, v))
    elif isinstance(env, Environment):
        env.activate(
            kv_consumer=lambda k, v: exports.append(Environment.tostring_export(k, v)), file_consumer=lambda f: exports.append(Environment.tostring_file(f))
        )
    shell_command = "".join(exports)
    for a in args:
        shell_command += ' "{0}"'.format(a)
    return [LeafSettings.DEFAULT_SHELL.value, "-c", shell_command]


def execute_command(*args, cwd=None, env=None, print_stdout=False):
    """
    Execute a process and returns the return code.
    The command is run in a leaf default shell (see settings) $SHELL -c
    and the env is set via multiple export/source commands to preserve variable overriding
    """
    # Builds args
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.STDOUT}
    if print_stdout:
        kwargs["stdout"] = None
        kwargs["stderr"] = None
    if cwd is not None:
        kwargs["cwd"] = str(cwd)
    # Execute the command
    return subprocess.call(build_shell_command(*args, env=env), **kwargs)


def is_latest_package(pi):
    """
    Used to check if the given PackageIdentifier version is *latest*
    """
    return pi.version == LeafConstants.LATEST


def find_latest_version(pi_or_name, pilist, ignore_unknown=False):
    """
    Use given package name to return the PackageIdentifier with the highest version
    """
    out = None
    piname = pi_or_name.name if isinstance(pi_or_name, PackageIdentifier) else str(pi_or_name)
    for pi in [pi for pi in pilist if pi.name == piname]:
        if out is None or pi > out:
            out = pi
    if out is None and not ignore_unknown:
        raise InvalidPackageNameException(pi_or_name)
    return out


def find_manifest(pi, mfmap, ignore_unknown=False):
    """
    Return the Manifest from the given map from its PackageIdentifier.
    If the given PackageIdentifier is *latest*, then return the highest version of the package.
    """
    if not isinstance(mfmap, dict):
        raise ValueError()
    if is_latest_package(pi):
        pi = find_latest_version(pi, mfmap.keys(), ignore_unknown=True)
    if pi in mfmap:
        return mfmap[pi]
    if not ignore_unknown:
        raise InvalidPackageNameException(pi)


def find_manifest_list(pilist, mfmap, ignore_unknown=False):
    """
    Return the list of Manifest from the given map from their PackageIdentifier.
    If the given PackageIdentifier is *latest*, then return the highest version of the package.
    """
    out = []
    for pi in pilist:
        mf = find_manifest(pi, mfmap, ignore_unknown=ignore_unknown)
        if mf is not None and mf not in out:
            out.append(mf)
    return out


def group_package_identifiers_by_name(pilist, pkgmap=None) -> dict:
    out = pkgmap if pkgmap is not None else {}
    for pi in pilist:
        if not isinstance(pi, PackageIdentifier):
            raise ValueError()
        current_pilist = out.get(pi.name)
        if current_pilist is None:
            current_pilist = []
            out[pi.name] = current_pilist
        if pi not in current_pilist:
            current_pilist.append(pi)
    for pkgname in out:
        out[pkgname] = sorted(out[pkgname])
    return out


def keep_latest(pilist: list) -> list:
    pkgmap = {}
    for pi in pilist:
        if pi.name not in pkgmap or pi > pkgmap[pi.name]:
            pkgmap[pi.name] = pi
    return sorted(pkgmap.values())

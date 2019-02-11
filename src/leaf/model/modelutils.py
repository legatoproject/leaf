
import os
import subprocess
from builtins import sorted

from leaf.core.constants import LeafConstants
from leaf.core.error import InvalidPackageNameException
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.model.steps import VariableResolver


def executeCommand(*args, cwd=None, env=None, shell=True, displayStdout=False):
    '''
    Execute a process and returns the return code.
    If 'shell' is set (true means bash, else set the string value), then the command is run in a $SHELL -c
    and the env is set via multiple export commands to preserve variable overriding
    '''

    # Builds args
    kwargs = {'stdout': subprocess.DEVNULL,
              'stderr': subprocess.STDOUT}
    if displayStdout:
        kwargs['stdout'] = None
        kwargs['stderr'] = None
    if cwd is not None:
        kwargs['cwd'] = str(cwd)

    # Build the command line
    command = None
    if isinstance(shell, str) or shell is True:
        # In shell mode, env is evaluated in the command line
        shellCmd = ''
        if isinstance(env, dict):
            for k, v in env.items():
                shellCmd += 'export %s="%s";' % (k, v)
        elif isinstance(env, Environment):
            for k, v in env.toList():
                shellCmd += 'export %s="%s";' % (k, v)
        for arg in args:
            shellCmd += ' "%s"' % arg
        if not isinstance(shell, str):
            shell = LeafConstants.DEFAULT_SHELL
        command = [shell, '-c', shellCmd]
    else:
        # invoke process directly
        if isinstance(env, dict):
            customEnv = dict(os.environ)
            for k, v in env.items():
                customEnv[k] = str(v)
            kwargs['env'] = customEnv
        elif isinstance(env, Environment):
            customEnv = dict(os.environ)
            for k, v in env.toList():
                customEnv[k] = str(v)
            kwargs['env'] = customEnv
        command = args

    # Execute the command
    return subprocess.call(command, **kwargs)


def isLatestPackage(pi):
    '''
    Used to check if the given PackageIdentifier version is *latest*
    '''
    return pi.version == LeafConstants.LATEST


def findLatestVersion(pi_or_piName, piList,
                      ignoreUnknown=False):
    '''
    Use given package name to return the PackageIdentifier with the highest version
    '''
    out = None
    piName = pi_or_piName.name if isinstance(
        pi_or_piName, PackageIdentifier) else str(pi_or_piName)
    for pi in [pi for pi in piList if pi.name == piName]:
        if out is None or pi > out:
            out = pi
    if out is None and not ignoreUnknown:
        raise InvalidPackageNameException(pi_or_piName)
    return out


def findManifest(pi, mfMap,
                 ignoreUnknown=False):
    '''
    Return the Manifest from the given map from its PackageIdentifier.
    If the given PackageIdentifier is *latest*, then return the highest version of the package.
    '''
    if not isinstance(mfMap, dict):
        raise ValueError()
    if isLatestPackage(pi):
        pi = findLatestVersion(pi, mfMap.keys(), ignoreUnknown=True)
    if pi in mfMap:
        return mfMap[pi]
    if not ignoreUnknown:
        raise InvalidPackageNameException(pi)


def groupPackageIdentifiersByName(piList, pkgMap=None, sort=True):
    out = pkgMap if pkgMap is not None else {}
    for pi in piList:
        if not isinstance(pi, PackageIdentifier):
            raise ValueError()
        currentPiList = out.get(pi.name)
        if currentPiList is None:
            currentPiList = []
            out[pi.name] = currentPiList
        if pi not in currentPiList:
            currentPiList.append(pi)
    if sort:
        for pkgName in out:
            out[pkgName] = sorted(out[pkgName])
    return out


def packageListToEnvironnement(ipList, ipMap, env=None):
    if env is None:
        env = Environment()
    for ip in ipList:
        ipEnv = Environment("Exported by package %s" % ip.getIdentifier())
        env.addSubEnv(ipEnv)
        vr = VariableResolver(ip, ipMap.values())
        for key, value in ip.getEnvMap().items():
            ipEnv.env.append((key,
                              vr.resolve(value)))
    return env

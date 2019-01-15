
import os
import re
import subprocess
from builtins import sorted

from leaf.constants import JsonConstants, LeafConstants
from leaf.core.dependencies import DependencyUtils
from leaf.core.error import InvalidPackageNameException
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier


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


def retrievePackageIdentifier(motif, validPiList):
    '''
    If only package name is given retrieve the latest package in given list
    with same package name
    '''
    if PackageIdentifier.isValidIdentifier(motif):
        return PackageIdentifier.fromString(motif)
    out = None
    if validPiList is not None:
        for pi in validPiList:
            if pi.name == motif:
                if out is None or pi > out:
                    out = pi
    if out is None:
        raise InvalidPackageNameException(motif)
    return out


def retrievePackage(pi, pkgMap):
    if pi not in pkgMap:
        raise InvalidPackageNameException(pi)
    return pkgMap[pi]


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


class VariableResolver():

    _PATTERN = "@{(NAME|VERSION|DIR)(?::((%s)%s(%s)))?}" % (PackageIdentifier.NAME_PATTERN,
                                                            PackageIdentifier.SEPARATOR,
                                                            PackageIdentifier.VERSION_PATTERN)

    def __init__(self, currentPkg=None, otherPkgList=None):
        self.currentPackage = currentPkg
        self.allPackages = {}
        if otherPkgList is not None:
            for pkg in otherPkgList:
                self.allPackages[pkg.getIdentifier()] = pkg
        if currentPkg is not None:
            self.allPackages[currentPkg.getIdentifier()] = currentPkg

    def getValue(self, var, pis):
        pkg = None
        if pis is None:
            # No PI specified means current package
            pkg = self.currentPackage
        else:
            pkg = DependencyUtils.findManifest(
                PackageIdentifier.fromString(pis),
                self.allPackages,
                ignoreUnknown=True)
        if pkg is not None:
            if var == 'NAME':
                return pkg.getIdentifier().name
            if var == 'VERSION':
                return pkg.getIdentifier().version
            if var == 'DIR':
                return str(pkg.folder)

    def resolve(self, value):
        def myReplace(m):
            out = self.getValue(m.group(1), m.group(2))
            if out is None:
                raise ValueError(
                    "Cannot resolve variable: %s" % m.group(0))
            return out

        return re.sub(VariableResolver._PATTERN, myReplace, value)


class StepExecutor():
    '''
    Used to execute post install & pre uninstall steps
    '''

    def __init__(self, logger, package, variableResolver, env=None):
        self.logger = logger
        self.package = package
        self.env = env
        self.targetFolder = package.folder
        self.variableResolver = variableResolver

    def postInstall(self,):
        self.runSteps(self.package.jsonget(
            JsonConstants.INSTALL, default=[]),
            label="install")

    def preUninstall(self):
        self.runSteps(self.package.jsonget(
            JsonConstants.UNINSTALL, default=[]),
            label="uninstall")

    def sync(self):
        self.runSteps(self.package.jsonget(
            JsonConstants.SYNC, default=[]),
            label="sync")

    def runSteps(self, steps, label):
        if steps is not None and len(steps) > 0:
            self.logger.printDefault("Run %s steps for %s" %
                                     (label, self.package.getIdentifier()))
            for step in steps:
                if JsonConstants.STEP_LABEL in step:
                    self.logger.printDefault(step[JsonConstants.STEP_LABEL])
                self.doExec(step, label)

    def doExec(self, step, label):
        command = [self.resolve(arg)
                   for arg in step[JsonConstants.STEP_EXEC_COMMAND]]
        self.logger.printVerbose("Execute:", ' '.join(command))
        env = Environment()
        env.addSubEnv(self.env)
        env.addSubEnv(Environment(
            content=step.get(JsonConstants.STEP_EXEC_ENV)))
        verbose = step.get(JsonConstants.STEP_EXEC_VERBOSE, False)
        shell = step.get(JsonConstants.STEP_EXEC_SHELL, True)

        rc = executeCommand(*command,
                            cwd=self.targetFolder,
                            env=env,
                            displayStdout=verbose or self.logger.isVerbose(),
                            shell=shell)
        if rc != 0:
            self.logger.printVerbose("Command '%s' exited with %s" %
                                     (" ".join(command), rc))
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose("Step ignores failure")
            else:
                raise ValueError("Error during %s step for %s" %
                                 (label, self.package.getIdentifier()))

    def resolve(self, value, prefixWithFolder=False):
        out = self.variableResolver.resolve(value)
        if prefixWithFolder:
            return str(self.targetFolder / out)
        return out

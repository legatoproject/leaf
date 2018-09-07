
from leaf.constants import JsonConstants
import os
import subprocess

from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.core.error import InvalidPackageNameException


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

    def __init__(self, currentPkg=None, otherPkgList=None):
        self.content = {}
        if currentPkg is not None:
            self.useInstalledPackage(currentPkg, True)
        if otherPkgList is not None:
            for pkg in otherPkgList:
                self.useInstalledPackage(pkg)

    def useInstalledPackage(self, pkg, isCurrentPkg=False):
        suffix = "" if isCurrentPkg else (":%s" % pkg.getIdentifier())
        self.addVariable("DIR" + suffix, pkg.folder)
        self.addVariable("NAME" + suffix, pkg.getIdentifier().name)
        self.addVariable("VERSION" + suffix, pkg.getIdentifier().version)

    def addVariable(self, k, v):
        self.content["@{%s}" % k] = v

    def resolve(self, value, failOnUnknownVariable=True):
        out = value
        for k, v in self.content.items():
            out = out.replace(k, str(v))
        if failOnUnknownVariable and '@{' in out:
            raise ValueError("Cannot resolve all variables in: %s" % out)
        return out


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
        env = dict(os.environ)
        for k, v in step.get(JsonConstants.STEP_EXEC_ENV, {}).items():
            v = self.resolve(v)
            env[k] = v
        if self.env is not None:
            env.update(self.env.toMap())
        stdout = subprocess.DEVNULL
        if self.logger.isVerbose() or step.get(JsonConstants.STEP_EXEC_VERBOSE,
                                               False):
            stdout = None
        rc = subprocess.call(command,
                             cwd=str(self.targetFolder),
                             env=env,
                             stdout=stdout,
                             stderr=subprocess.STDOUT)
        if rc != 0:
            self.logger.printVerbose("Command '%s' exited with %s" %
                                     (" ".join(command), rc))
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose("Step ignores failure")
            else:
                raise ValueError("Error during %s step for %s" %
                                 (label, self.package.getIdentifier()))

    def resolve(self, value,
                failOnUnknownVariable=True, prefixWithFolder=False):
        out = self.variableResolver.resolve(
            value,
            failOnUnknownVariable=failOnUnknownVariable)
        if prefixWithFolder:
            return str(self.targetFolder / out)
        return out

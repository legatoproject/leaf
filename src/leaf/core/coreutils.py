
import os
import subprocess

from leaf import __version__
from leaf.constants import JsonConstants
from leaf.model.base import Environment


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
        steps = self.package.jsonpath(JsonConstants.INSTALL, default=[])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Post-install")

    def preUninstall(self):
        steps = self.package.jsonpath(JsonConstants.UNINSTALL, default=[])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Pre-uninstall")

    def runSteps(self, steps, ip, label=""):
        self.logger.progressStart('Execute steps', total=len(steps))
        worked = 0
        for step in steps:
            if JsonConstants.STEP_LABEL in step:
                self.logger.printDefault(step[JsonConstants.STEP_LABEL])
            self.doExec(step)
            worked += 1
            self.logger.progressWorked('Execute steps',
                                       worked=worked,
                                       total=len(steps))
        self.logger.progressDone('Execute steps')

    def doExec(self, step):
        command = [self.resolve(arg)
                   for arg in step[JsonConstants.STEP_EXEC_COMMAND]]
        self.logger.printVerbose("Exec:", ' '.join(command))
        env = dict(os.environ)
        for k, v in step.get(JsonConstants.STEP_EXEC_ENV, {}).items():
            v = self.resolve(v)
            env[k] = v
        if self.env is not None:
            env.update(self.env.toMap())
        env["LEAF_VERSION"] = str(__version__)
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
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose("Return code is",
                                         rc,
                                         "but step ignores failure")
            else:
                raise ValueError("Step exited with return code " + str(rc))

    def resolve(self, value, failOnUnknownVariable=True, prefixWithFolder=False):
        out = self.variableResolver.resolve(value,
                                            failOnUnknownVariable=failOnUnknownVariable)
        if prefixWithFolder:
            return str(self.targetFolder / out)
        return out
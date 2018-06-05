'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from enum import unique, IntEnum
from leaf import __version__
from leaf.constants import JsonConstants
from leaf.model import Manifest, Environment, PackageIdentifier
import os
import subprocess


def genEnvScript(env, activateFile=None, deactivateFile=None):
    '''
    Generates environment script to activate and desactivate a profile
    '''
    if deactivateFile is not None:
        resetMap = OrderedDict()
        for k in env.keys():
            resetMap[k] = os.environ.get(k)
        with open(str(deactivateFile), "w") as fp:
            for k, v in resetMap.items():
                # If the value was not present in env before, reset it
                if v is None:
                    fp.write(Environment.unsetCommand(k) + "\n")
                else:
                    fp.write(Environment.exportCommand(k, v) + "\n")
    if activateFile is not None:
        with open(str(activateFile), "w") as fp:

            def commentConsumer(c):
                fp.write(Environment.comment(c) + "\n")

            def kvConsumer(k, v):
                fp.write(Environment.exportCommand(k, v) + "\n")

            env.printEnv(kvConsumer=kvConsumer,
                         commentConsumer=commentConsumer)


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


class TagManager():
    '''
    Class used to tag packages
    '''

    LATEST = 'latest'
    INSTALLED = 'installed'
    CURRENT = 'current'

    def tagLatest(self, mfList):
        '''
        Add the 'latest' tag to packages with the latest version
        '''
        mapByName = OrderedDict()
        for mf in mfList:
            pkgName = mf.getIdentifier().name
            if pkgName not in mapByName:
                mapByName[pkgName] = []
            mapByName[pkgName].append(mf)
        for pkgList in mapByName.values():
            latest = next(iter(sorted(pkgList,
                                      key=Manifest.getIdentifier,
                                      reverse=True)))
            latest.customTags.append(TagManager.LATEST)

    def tagInstalled(self, mfList, piList):
        '''
        Tag packages from given mfList as installed if they are in the given piList 
        '''
        for mf in mfList:
            if mf.getIdentifier() in piList:
                mf.customTags.append(TagManager.INSTALLED)

    def tagCurrent(self, mfList, pf):
        '''
        Tag packages in mfList as current if they are in the given profile
        '''
        for mf in mfList:
            if str(mf.getIdentifier()) in pf.getPackages():
                mf.customTags.append(TagManager.CURRENT)


@unique
class DependencyType(IntEnum):
    INSTALLED = 1
    AVAILABLE = 2
    INSTALL = 3
    UNINSTALL = 4
    PREREQ = 5


@unique
class DependencyStrategy(IntEnum):
    ALL_VERSIONS = 0
    LATEST_VERSION = 1


class DependencyManager():
    '''
    Used to build the dependency tree using dynamic conditions
    '''

    @staticmethod
    def _find(pi, mfMap,
              latestVersions=None,
              ignoreUnknown=False):
        '''
        Return a Manifest given a PackageIdentifier
        '''
        if latestVersions is not None and pi.name in latestVersions:
            pi = latestVersions[pi.name]
        if pi not in mfMap and not ignoreUnknown:
            raise ValueError("Cannot find package %s" % pi)
        return mfMap.get(pi)

    @staticmethod
    def _getLatestVersions(piList):
        '''
        Build a dist of name/pi of the latest versions of given pi list
        '''
        out = {}
        for pi in piList:
            if pi.name not in out or out[pi.name] < pi:
                out[pi.name] = pi
        return out

    @staticmethod
    def _buildTree(piList,
                   mfMap,
                   out,
                   env=None,
                   strategy=DependencyStrategy.ALL_VERSIONS,
                   latestVersions=None,
                   ignoredPiList=None,
                   ignoreUnknown=False):
        '''
        Build a manifest list of given PackageIdentifiers and its dependecies
        @return: Manifest list
        '''
        if ignoredPiList is None:
            ignoredPiList = []
        for pi in piList:
            if pi not in ignoredPiList:
                ignoredPiList.append(pi)
                mf = DependencyManager._find(pi, mfMap,
                                             latestVersions=latestVersions,
                                             ignoreUnknown=ignoreUnknown)
                if mf is not None and mf not in out:
                    # Begin by adding dependencies
                    DependencyManager._buildTree(mf.getLeafDependsFromEnv(env),
                                                 mfMap,
                                                 out,
                                                 env=env,
                                                 strategy=strategy,
                                                 latestVersions=latestVersions,
                                                 ignoredPiList=ignoredPiList,
                                                 ignoreUnknown=ignoreUnknown)
                    out.append(mf)

        if strategy == DependencyStrategy.LATEST_VERSION and latestVersions is None:
            # Ignore all 'non-latest versions'
            latestVersions = DependencyManager._getLatestVersions(
                map(Manifest.getIdentifier, out))
            # Reset out
            del out[:]
            # Reinvoke and give latest versions,
            # NB reset ignoredPiList to restart algo
            DependencyManager._buildTree(piList,
                                         mfMap,
                                         out,
                                         env=env,
                                         strategy=strategy,
                                         latestVersions=latestVersions,
                                         ignoreUnknown=ignoreUnknown)

    @staticmethod
    def compute(piList,
                depType,
                strategy=DependencyStrategy.ALL_VERSIONS,
                apMap=None,
                ipMap=None,
                env=None,
                ignoreUnknown=False):
        out = []
        if depType == DependencyType.AVAILABLE:
            if apMap is None:
                raise ValueError()
            # In case of available, only build the list
            DependencyManager._buildTree(piList, apMap, out,
                                         env=env,
                                         strategy=strategy,
                                         ignoreUnknown=ignoreUnknown)
        elif depType == DependencyType.INSTALLED:
            if ipMap is None:
                raise ValueError()
            # In case of installed, only build the list
            DependencyManager._buildTree(piList, ipMap, out,
                                         env=env,
                                         strategy=strategy,
                                         ignoreUnknown=ignoreUnknown)
        elif depType == DependencyType.INSTALL:
            if ipMap is None or apMap is None:
                raise ValueError()
            # Build the list from available packages
            DependencyManager._buildTree(piList, apMap, out,
                                         env=env,
                                         strategy=strategy,
                                         ignoreUnknown=False)
            # Remove already installed packages
            out = [ap for ap in out if ap.getIdentifier() not in ipMap]
        elif depType == DependencyType.UNINSTALL:
            if ipMap is None:
                raise ValueError()
            # Build the list from available packages
            DependencyManager._buildTree(piList, ipMap, out,
                                         ignoreUnknown=True)
            # for uninstall, reverse order
            out = list(reversed(out))
            # Maintain dependencies
            for neededIp in DependencyManager.compute([ip.getIdentifier() for ip in ipMap.values() if ip not in out],
                                                      DependencyType.INSTALLED,
                                                      strategy=strategy,
                                                      ipMap=ipMap,
                                                      ignoreUnknown=True):
                if neededIp in out:
                    out.remove(neededIp)
        elif depType == DependencyType.PREREQ:
            # First get the install tree
            apList = DependencyManager.compute(piList,
                                               DependencyType.INSTALL,
                                               strategy=strategy,
                                               apMap=apMap,
                                               ipMap=ipMap,
                                               env=env)
            prereqPiList = set()
            # Get all prereq PI
            for ap in apList:
                prereqPiList.update(map(PackageIdentifier.fromString,
                                        ap.getLeafRequires()))
            # return a list of AP
            out = [DependencyManager._find(pi, apMap) for pi in prereqPiList]
            # sort alphabetically
            out = list(sorted(out, key=Manifest.getIdentifier))
        else:
            raise ValueError()
        return out


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

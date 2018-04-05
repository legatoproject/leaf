'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from leaf import __version__
from leaf.constants import LeafConstants, JsonConstants
from leaf.model import PackageIdentifier, Manifest
from leaf.utils import downloadFile
import os
import shutil
import subprocess


class TagManager():

    def tagLatest(self, mfList):
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
            latest.tags.append("latest")

    def tagInstalled(self, mfList, piList):
        for mf in mfList:
            if mf.getIdentifier() in piList:
                mf.tags.append("installed")

    def tagCurrent(self, mfList, pf):
        for mf in mfList:
            if str(mf.getIdentifier()) in pf.getPackages():
                mf.tags.append("current")


class DependencyManager():

    def __init__(self):
        self.content = OrderedDict()

    def addContent(self, mfMap, clear=False):
        if clear:
            self.content.clear()
        for pi, mf in mfMap.items():
            if pi not in self.content:
                self.content[pi] = mf

    def resolve(self, pi):
        out = self.content.get(pi)
        if out is None:
            raise ValueError("Cannot find package: " + str(pi))
        return out

    def getDependencyTree(self, piList, acc=None):
        '''
        Return the list of PackageIdentifiers of the given list plus all needed dependencies
        @return: PackageIdentifiers list
        '''
        out = [] if acc is None else acc
        for pi in piList:
            if pi not in out:
                mf = self.resolve(pi)
                out.append(pi)
                self.getDependencyTree(
                    PackageIdentifier.fromStringList(mf.getLeafDepends()),
                    acc=out)
        return out

    def filterAndSort(self, piList, reverse=False, ignoredPiList=None):
        '''
        Sort and filter the given PackageIdentifiers
        @return: PackageIdentifiers list
        '''
        out = []

        def checker(mf):
            for pi in PackageIdentifier.fromStringList(mf.getLeafDepends()):
                if pi in out:
                    continue
                if ignoredPiList is not None and pi in ignoredPiList:
                    continue
                return False
            return True

        piList = list(piList)
        # Ordering
        while len(piList) > 0:
            for pi in piList:
                mf = self.content[pi]
                if mf is None:
                    raise ValueError('Cannot sort dependency list')
                if checker(mf):
                    out.append(pi)
            piList = [pi for pi in piList if pi not in out]
        # filter
        if ignoredPiList is not None:
            out = [pi for pi in out if pi not in ignoredPiList]
        # reverse
        if reverse:
            out.reverse()
        return out

    def filterMissingDependencies(self, piList):
        '''
        Returns the list of PackageIdentifiers not in internal content
        @return: PackageIdentifier list
        '''
        return [pi for pi in piList if pi not in self.content]

    def maintainDependencies(self, piList):
        '''
        @return: PackageIdentifiers list
        '''
        otherPiList = [pi for pi in self.content.keys() if pi not in piList]
        keepList = self.getDependencyTree(otherPiList)
        return [pi for pi in piList if pi not in keepList]


class StepExecutor():
    '''
    Used to execute post install & pre uninstall steps
    '''

    def __init__(self, logger, package, otherPackages, extraEnv=None):
        self.logger = logger
        self.package = package
        self.extraEnv = extraEnv
        self.targetFolder = package.folder
        self.variables = dict()
        self.variables[LeafConstants.VAR_PREFIX +
                       "{DIR}"] = str(package.folder)
        self.variables[LeafConstants.VAR_PREFIX +
                       "{NAME}"] = package.getName()
        self.variables[LeafConstants.VAR_PREFIX +
                       "{VERSION}"] = package.getVersion()
        for pi, pack in otherPackages.items():
            key = "%s{DIR:%s}" % (LeafConstants.VAR_PREFIX, str(pi))
            self.variables[key] = str(pack.folder)

    def postInstall(self, ):
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
            stepType = step[JsonConstants.STEP_TYPE]
            if stepType == JsonConstants.STEP_EXEC:
                self.doExec(step)
            elif stepType == JsonConstants.STEP_COPY:
                self.doCopy(step)
            elif stepType == JsonConstants.STEP_LINK:
                self.doLink(step)
            elif stepType == JsonConstants.STEP_DELETE:
                self.doDelete(step)
            elif stepType == JsonConstants.STEP_DOWNLOAD:
                self.doDownload(step, ip)
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
        if self.extraEnv is not None:
            env.update(self.extraEnv)
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

    def doCopy(self, step):
        src = self.resolve(
            step[JsonConstants.STEP_COPY_SOURCE], prefixWithFolder=True)
        dst = self.resolve(
            step[JsonConstants.STEP_COPY_DESTINATION], prefixWithFolder=True)
        self.logger.printVerbose("Copy:", src, "->", dst)
        shutil.copy2(src, dst)

    def doLink(self, step):
        target = self.resolve(
            step[JsonConstants.STEP_LINK_NAME], prefixWithFolder=True)
        source = self.resolve(
            step[JsonConstants.STEP_LINK_TARGET], prefixWithFolder=True)
        self.logger.printVerbose("Link:", source, " -> ", target)
        os.symlink(source, target)

    def doDelete(self, step):
        for file in step[JsonConstants.STEP_DELETE_FILES]:
            resolvedFile = self.resolve(file, prefixWithFolder=True)
            self.logger.printVerbose("Delete:", resolvedFile)
            os.remove(resolvedFile)

    def doDownload(self, step, ip):
        try:
            downloadFile(step[JsonConstants.STEP_DOWNLOAD_URL],
                         self.targetFolder,
                         self.logger,
                         step.get(JsonConstants.STEP_DOWNLOAD_FILENAME),
                         step.get(JsonConstants.STEP_DOWNLOAD_SHA1SUM))
        except Exception as e:
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose(
                    "Download failed, but step ignores failure")
            else:
                raise e

    def resolve(self, value, failOnUnknownVariable=True, prefixWithFolder=False):
        out = str(value)
        for key, value in self.variables.items():
            out = out.replace(key, value)
        if failOnUnknownVariable and (LeafConstants.VAR_PREFIX + '{') in out:
            raise ValueError("Cannot resolve all variables for: " + out)
        if prefixWithFolder:
            return str(self.targetFolder / out)
        return out

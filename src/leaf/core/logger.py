'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import ABC, abstractmethod
from cProfile import label
from collections import OrderedDict
from enum import IntEnum, unique
import json
from leaf.constants import LeafConstants
import os
import sys

from leaf.core.workspacemanager import WorkspaceManager
from leaf.model.base import Environment
from leaf.model.package import AvailablePackage, InstalledPackage, Manifest,\
    LeafArtifact
from leaf.model.remote import Remote
from leaf.model.workspace import Profile


@unique
class Verbosity(IntEnum):
    QUIET = 0
    DEFAULT = 1
    VERBOSE = 2


def createLogger(args, nonInteractive):
    '''
    Returns the correct ILogger
    '''
    if len(os.environ.get(LeafConstants.ENV_JSON_OUTPUT, "")) > 0:
        return JsonLogger()
    verbosity = Verbosity.DEFAULT
    if hasattr(args, 'verbosity'):
        verbosity = getattr(args, 'verbosity')
    return TextLogger(verbosity, nonInteractive)


class ILogger(ABC):
    '''
    Logger interface
    '''

    def __init__(self, verbosity):
        self.verbosity = verbosity

    def getVerbosity(self):
        return self.verbosity

    def isQuiet(self):
        return self.getVerbosity() == Verbosity.QUIET

    def isVerbose(self):
        return self.getVerbosity() == Verbosity.VERBOSE

    @abstractmethod
    def printQuiet(self, *message, **kwargs):
        pass

    @abstractmethod
    def printDefault(self, *message, **kwargs):
        pass

    @abstractmethod
    def printVerbose(self, *message, **kwargs):
        pass

    @abstractmethod
    def printError(self, *message):
        pass

    @abstractmethod
    def progressStart(self, task, message=None, total=-1):
        pass

    @abstractmethod
    def progressWorked(self, task, message=None, worked=0, total=100, sameLine=False):
        pass

    @abstractmethod
    def progressDone(self, task, message=None):
        pass

    @abstractmethod
    def displayItem(self, item):
        pass

    @abstractmethod
    def confirm(self,
                question="Do you want to continue?",
                yes=["y"],
                no=["n"],
                failOnDecline=False):
        pass


class TextLogger (ILogger):
    '''
    Prints a lot of information
    '''

    def __init__(self, verbosity, nonInteractive=True):
        ILogger.__init__(self, verbosity)
        self.nonInteractive = nonInteractive

    def printQuiet(self, *message, **kwargs):
        if self.verbosity >= Verbosity.QUIET:
            print(*message, **kwargs)

    def printDefault(self, *message, **kwargs):
        if self.verbosity >= Verbosity.DEFAULT:
            print(*message, **kwargs)

    def printVerbose(self, *message, **kwargs):
        if self.verbosity >= Verbosity.VERBOSE:
            print(*message, **kwargs)

    def printError(self, *message):
        print(*message, file=sys.stderr)

    def progressStart(self, task, message=None, total=-1):
        if message is not None:
            self.printDefault(message)

    def progressWorked(self, task, message=None, worked=0, total=100, sameLine=False):
        if message is not None:
            if total > 100 and worked <= total:
                message = "[%d%%] %s" % (worked * 100 / total, message)
            else:
                message = "[%d/%d] %s" % (worked, total, message)
            self.printDefault(message, end='\r' if sameLine else '\n')

    def progressDone(self, task, message=None):
        if message is not None:
            self.printDefault(message)

    def displayItem(self, item):
        if isinstance(item, Environment):
            def commentConsumer(c):
                print(Environment.comment(c))

            def kvConsumer(k, v):
                print(Environment.exportCommand(k, v))

            item.printEnv(kvConsumer=kvConsumer,
                          commentConsumer=None if self.isQuiet() else commentConsumer)
        elif isinstance(item, WorkspaceManager):
            print("Workspace %s" % item.rootFolder)
            if self.isVerbose():
                wsc = item.readConfiguration()
                content = OrderedDict()
                content["Workspace env"] = wsc.getEnvMap()
                self.prettyprintContent(content)
            if not self.isQuiet():
                for pf in item.getAllProfiles().values():
                    label = pf.name
                    if pf.isCurrentProfile:
                        label += " [current]"
                    print(" - " + label)
                    content = OrderedDict()
                    content["Packages"] = pf.getPackages()
                    if self.isVerbose():
                        content["Env"] = pf.getEnvMap()
                        content["Sync"] = item.isProfileSync(pf)
                        content["Packages"] = pf.getPackages()
                    self.prettyprintContent(content)
        elif isinstance(item, Profile):
            text = item.name
            if item.isCurrentProfile and not self.isQuiet():
                text += " [current]"
            print(text)
            if self.isVerbose():
                content = OrderedDict()
                content["Packages"] = item.getPackages()
                content["Env"] = item.getEnvMap()
                self.prettyprintContent(content)
        elif isinstance(item, LeafArtifact):
            if self.verbosity == Verbosity.QUIET:
                print(item.path)
            else:
                print(item.getIdentifier(), "->", item.path)
        elif isinstance(item, Manifest):
            itemLabel = str(item.getIdentifier())
            if self.verbosity == Verbosity.DEFAULT and len(item.getAllTags()) > 0:
                itemLabel += " (%s)" % ",".join(item.getAllTags())
            print(itemLabel)
            if self.isVerbose():
                content = OrderedDict()
                content["Description"] = item.getDescription()
                if isinstance(item, AvailablePackage):
                    content["Size"] = (item.getSize(), 'bytes')
                    content["Source"] = item.getUrl()
                elif isinstance(item, InstalledPackage):
                    content["Folder"] = item.folder
                content["Depends"] = item.getLeafDepends()
                content["Requires"] = item.getLeafRequires()
                content["Tags"] = item.getAllTags()
                self.prettyprintContent(content)
        elif isinstance(item, Remote):
            if self.isQuiet():
                print(item.alias)
            elif self.isVerbose():
                print(item.alias)
                content = OrderedDict()
                content["Url"] = item.getUrl()
                if item.isFetched():
                    content["Name"] = item.getInfoName()
                    content["Description"] = item.getInfoDescription()
                    content["Last update"] = item.getInfoDate()
                content["Enabled"] = item.isEnabled()
                self.prettyprintContent(content)
            else:
                label = "%s [%s]" % (item.alias, item.getUrl())
                if not item.isEnabled():
                    label += " (disabled)"
                print(label)
        elif isinstance(item, tuple) and len(item) == 2:
            print('export %s="%s"; ' % item)
        elif item is not None:
            print(str(item))

    def prettyprintContent(self, content, indent=4, separator=':', ralign=False):
        '''
        Display formatted content
        '''
        if content is not None:
            indentString = ' ' * indent
            for key, value in content.items():
                if isinstance(value, (list, tuple)):
                    if len(value) > 0:
                        text = ', '.join(map(str, value))
                        print(indentString,
                              key + separator,
                              text)
                elif isinstance(value, dict):
                    if len(value) > 0:
                        text = ', '.join(["%s=%s" % (k, v)
                                          for (k, v) in value.items()])
                        print(indentString,
                              key + separator,
                              text)
                elif value is not None:
                    text = str(value)
                    print(indentString,
                          key + separator,
                          text)

    def confirm(self,
                question="Do you want to continue?",
                yes=["y"],
                no=["n"],
                failOnDecline=False):
        label = " (%s/%s) " % (
            "/".join(map(str.upper, yes)),
            "/".join(map(str.lower, no)))
        while True:
            print(question, label)
            if self.nonInteractive:
                return True
            answer = input().strip()
            if answer == "":
                return True
            if answer.lower() in map(str.lower, yes):
                return True
            if answer.lower() in map(str.lower, no):
                if failOnDecline:
                    raise ValueError("Operation aborted")
                return False


class JsonLogger(ILogger):
    '''
    Print information in a machine readable format (json)
    '''

    def __init__(self):
        ILogger.__init__(self, Verbosity.VERBOSE)

    def printJson(self, content):
        print(json.dumps(content, sort_keys=True, indent=None), flush=True)

    def progressStart(self, task, message=None, total=-1):
        self.printJson({
            'event': "progressStart",
            'task': task,
            'message': message,
            'total': total
        })

    def progressWorked(self, task, message=None, worked=0, total=100, sameLine=False):
        self.printJson({
            'event': "progressWorked",
            'task': task,
            'message': message,
            'worked': worked,
            'total': total
        })

    def progressDone(self, task, message=None):
        self.printJson({
            'event': "progressDone",
            'task': task,
            'message': message
        })

    def printQuiet(self, *message, **kwargs):
        self.printJson({
            'event': "message",
            'message': " ".join(map(str, message)),
        })

    def printDefault(self, *message, **kwargs):
        self.printJson({
            'event': "message",
            'message': " ".join(map(str, message)),
        })

    def printVerbose(self, *message, **kwargs):
        self.printJson({
            'event': "detail",
            'message': " ".join(map(str, message)),
        })

    def printError(self, *message):
        self.printJson({
            'event': "error",
            'message': " ".join(map(str, message)),
        })

    def displayJsonItem(self, itemType, json=None, extraMap=None):
        content = {
            'event': "item",
            'type': itemType,
        }
        if json is not None:
            content['data'] = json
        if extraMap is not None:
            for k, v in extraMap.items():
                if k not in content:
                    content[k] = None if v is None else str(v)
        self.printJson(content)
        pass

    def displayItem(self, item):
        itemType = None
        json = None
        extraMap = {}
        if isinstance(item, Environment):
            def commentConsumer(c):
                self.displayJsonItem("comment", extraMap={"comment": c})

            def kvConsumer(k, v):
                self.displayJsonItem("env", extraMap={"key": k, "value": v})

            item.printEnv(kvConsumer=kvConsumer,
                          commentConsumer=commentConsumer)
        elif isinstance(item, WorkspaceManager):
            itemType = "workspace"
            json = item.readConfiguration().json
            extraMap['folder'] = item.rootFolder
            try:
                extraMap['currentProfile'] = item.getCurrentProfileName()
            except:
                pass
        elif isinstance(item, Profile):
            itemType = "profile"
            json = item.json
            extraMap['name'] = item.name
            extraMap['folder'] = item.folder
            extraMap['isCurrentProfile'] = item.isCurrentProfile
        elif isinstance(item, Manifest):
            itemType = "package"
            json = item.json
            extraMap['customTags'] = ",".join(item.customTags)
            if isinstance(item, AvailablePackage):
                extraMap['url'] = item.getUrl()
            elif isinstance(item, InstalledPackage):
                extraMap['folder'] = item.folder
            elif isinstance(item, LeafArtifact):
                extraMap['path'] = item.path
        elif isinstance(item, Remote):
            itemType = "remote"
            json = item.json
            extraMap = {'alias': item.alias}
            if item.isFetched():
                extraMap["name"] = item.getInfoName()
                extraMap["description"] = item.getInfoDescription()
                extraMap["date"] = item.getInfoDate()
        elif isinstance(item, tuple) and len(item) == 2:
            itemType = "env"
            extraMap = {'key': item[0],
                        'value': item[1]}
        else:
            itemType = "string"
            extraMap = {'value': str(item)}
        if itemType is not None:
            self.displayJsonItem(itemType, json, extraMap)

    def confirm(self,
                question=None,
                yes=None,
                no=None,
                failOnDecline=False):
        self.printJson({
            'event': "confirm",
            'question': question
        })
        return True

'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import ABC, abstractmethod
from collections import OrderedDict
import json
from leaf.constants import JsonConstants, LeafConstants
from leaf.core import Workspace
from leaf.model import AvailablePackage, InstalledPackage, Manifest,\
    RemoteRepository, LeafArtifact, Profile
import os
import sys


def createLogger(verbose, quiet):
    '''
    Returns the correct ILogger
    '''
    if len(os.environ.get(LeafConstants.JSON_OUTPUT, "")) > 0:
        return JsonLogger()
    if verbose:
        return TextLogger(TextLogger.LEVEL_VERBOSE)
    if quiet:
        return TextLogger(TextLogger.LEVEL_QUIET)
    return TextLogger(TextLogger.LEVEL_DEFAULT)


class ILogger(ABC):
    '''
    Logger interface
    '''

    def isVerbose(self):
        return False

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


class TextLogger (ILogger):
    '''
    Prints a lot of information
    '''
    LEVEL_QUIET = 0
    LEVEL_DEFAULT = 1
    LEVEL_VERBOSE = 2

    def __init__(self, level):
        self.level = level

    def isVerbose(self):
        return self.level == TextLogger.LEVEL_VERBOSE

    def printQuiet(self, *message, **kwargs):
        if self.level >= TextLogger.LEVEL_QUIET:
            print(*message, **kwargs)

    def printDefault(self, *message, **kwargs):
        if self.level >= TextLogger.LEVEL_DEFAULT:
            print(*message, **kwargs)

    def printVerbose(self, *message, **kwargs):
        if self.level >= TextLogger.LEVEL_VERBOSE:
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
        if isinstance(item, Workspace):
            print("Workspace %s" % item.rootFolder)
            if self.isVerbose():
                wsc = item.readConfiguration()
                content = OrderedDict()
                content["Workspace env"] = wsc.getWsEnv()
                content["Remotes"] = wsc.getWsRemotes()
                content["Modules"] = wsc.getWsSupportedModules()
                self.prettyprintContent(content)

            for pf in item.getAllProfiles().values():
                print("-",
                      pf.name,
                      "[current]" if pf.isCurrentProfile else "")
                if self.isVerbose():
                    content = OrderedDict()
                    content["Packages"] = pf.getPackages()
                    content["Env"] = pf.getEnv()
                    self.prettyprintContent(content)
        elif isinstance(item, Profile):
            print(item.name,
                  "[current]" if item.isCurrentProfile else "")
            if self.isVerbose():
                content = OrderedDict()
                content["Packages"] = item.getPackages()
                content["Env"] = item.getEnv()
                self.prettyprintContent(content)
        elif isinstance(item, LeafArtifact):
            if self.level == TextLogger.LEVEL_QUIET:
                print(item.path)
            else:
                print(item.getIdentifier(), "->", item.path)
        elif isinstance(item, Manifest):
            print(item.getIdentifier())
            if self.isVerbose():
                content = OrderedDict()
                content["Description"] = item.getDescription()
                if isinstance(item, AvailablePackage):
                    content["Size"] = (item.getSize(), 'bytes')
                    content["Source"] = item.getUrl()
                elif isinstance(item, InstalledPackage):
                    content["Folder"] = item.folder
                content["Systems"] = item.getSupportedOS()
                content["Depends"] = item.getLeafDepends()
                content["Modules"] = item.getSupportedModules()
                self.prettyprintContent(content)
            pass
        elif isinstance(item, RemoteRepository):
            print(item.url)
            if self.isVerbose():
                content = OrderedDict()
                content["Root repository"] = item.isRootRepository
                if not item.isFetched():
                    content["Status"] = "not fetched yet"
                else:
                    content["Name"] = item.jsonpath(JsonConstants.INFO,
                                                    JsonConstants.REMOTE_NAME)
                    content["Description"] = item.jsonpath(JsonConstants.INFO,
                                                           JsonConstants.REMOTE_DESCRIPTION)
                    content["Last update"] = item.jsonpath(JsonConstants.INFO,
                                                           JsonConstants.REMOTE_DATE)
                self.prettyprintContent(content)
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


class JsonLogger(ILogger):
    '''
    Print information in a machine readable format (json)
    '''

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
                    content[k] = str(v)
        self.printJson(content)
        pass

    def displayItem(self, item):
        itemType = None
        json = None
        extraMap = {}
        if isinstance(item, Workspace):
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
            if isinstance(item, AvailablePackage):
                extraMap['url'] = item.getUrl()
            elif isinstance(item, InstalledPackage):
                extraMap['folder'] = item.folder
            elif isinstance(item, LeafArtifact):
                extraMap['path'] = item.path
        elif isinstance(item, RemoteRepository):
            itemType = "remote"
            json = item.json
            extraMap = {'url': item.url,
                        'isRootRepository': item.isRootRepository}
        elif isinstance(item, tuple) and len(item) == 2:
            itemType = "env"
            extraMap = {'key': item[0],
                        'value': item[1]}
        else:
            itemType = "string"
            extraMap = {'value': str(item)}

        self.displayJsonItem(itemType, json, extraMap)

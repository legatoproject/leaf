'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
import os


class JsonObject():
    '''
    Represent a json object
    '''

    def __init__(self, json):
        self.json = json

    def jsoninit(self, *path, key=None, value=None, force=False):
        if key is None:
            raise ValueError("Cannot init json")
        parent = self.jsonpath(*path)
        if not isinstance(parent, dict):
            raise ValueError("Cannot init json")
        if force or key not in parent:
            parent[key] = value
        return parent[key]

    def jsonpath(self, *path, default=None):
        '''
        Utility to browse json and reduce None testing
        '''
        currentNode = self.json
        for p in path:
            if isinstance(currentNode, dict) and p in currentNode:
                currentNode = currentNode.get(p, default)
            else:
                return default
        return currentNode


class Environment():

    @staticmethod
    def comment(line):
        return "# %s" % line

    @staticmethod
    def exportCommand(key, value):
        return "export %s=\"%s\";" % (key, value)

    @staticmethod
    def unsetCommand(key):
        return "unset %s;" % (key)

    def __init__(self, comment=None, content=None):
        self.comment = comment
        self.env = []
        self.children = []
        if isinstance(content, dict):
            self.env += content.items()
        elif isinstance(content, list):
            self.env += content

    def addSubEnv(self, child):
        if child is not None:
            if not isinstance(child, Environment):
                raise ValueError()
            self.children.append(child)

    def printEnv(self, kvConsumer=None, commentConsumer=None):
        if len(self.env) > 0:
            if self.comment is not None and commentConsumer is not None:
                commentConsumer(self.comment)
            if kvConsumer is not None:
                for k, v in self.env:
                    kvConsumer(k, v)
        for e in self.children:
            e.printEnv(kvConsumer, commentConsumer)

    def toList(self, acc=None):
        if acc is None:
            acc = []
        acc += self.env
        for e in self.children:
            e.toList(acc=acc)
        return acc

    def toMap(self):
        out = OrderedDict()
        for k in self.keys():
            out[k] = self.findValue(k)
        return out

    def keys(self):
        out = set()
        for k, _ in self.toList():
            out.add(k)
        return out

    def findValue(self, key):
        out = None
        for k, v in self.env:
            if k == key:
                out = str(v)
        for c in self.children:
            out2 = c.findValue(key)
            if out2 is not None:
                out = out2
        return out

    def unset(self, key):
        if key in self.env:
            del self.env[key]
        for c in self.children:
            c.unset(key)

    def generateScripts(self, activateFile=None, deactivateFile=None):
        '''
        Generates environment script to activate and desactivate a profile
        '''
        if deactivateFile is not None:
            resetMap = OrderedDict()
            for k in self.keys():
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

                self.printEnv(kvConsumer=kvConsumer,
                              commentConsumer=commentConsumer)

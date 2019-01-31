'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from enum import IntEnum, unique

from leaf.model.modelutils import layerModelDiff, layerModelUpdate
from leaf.utils import jsonLoadFile, jsonWriteFile


@unique
class Scope(IntEnum):
    LEAF = 0
    USER = 1
    WORKSPACE = 2
    PROFILE = 3
    PACKAGE = 4


class JsonObject():
    '''
    Represent a json object
    '''

    def __init__(self, json):
        self.json = json

    def has(self, *keys):
        for key in keys:
            if key not in self.json:
                return False
        return True

    def jsonget(self, key, default=None, mandatory=False):
        '''
        Utility to browse json and reduce None testing
        '''
        if key not in self.json:
            if mandatory:
                raise ValueError("Missing mandatory json field '%s'" % key)
            if default is not None:
                self.json[key] = default
        return self.json.get(key)

    def jsonpath(self, path, default=None, mandatory=False):
        '''
        Utility to browse json and reduce None testing
        '''
        if not isinstance(path, (list, tuple)):
            raise ValueError(type(path))
        if len(path) == 0:
            raise ValueError()
        if len(path) == 1:
            return self.jsonget(path[0], default=default, mandatory=mandatory)
        child = self.jsonget(path[0], mandatory=mandatory)
        if not isinstance(child, dict):
            raise ValueError()
        return JsonObject(child).jsonpath(path[1:], default=default, mandatory=mandatory)


class ConfigFileWithLayer(JsonObject):

    def __init__(self, *layerFiles, defaultFactory=OrderedDict):
        model = None
        for layer in layerFiles:
            if layer is not None and layer.is_file():
                if model is None:
                    model = jsonLoadFile(layer)
                else:
                    layerModelUpdate(model, jsonLoadFile(layer))
        JsonObject.__init__(
            self, model if model is not None else defaultFactory())
        self._checkModel()

    def _checkModel(self):
        '''
        Method used to check the model and do mandatory migration
        '''
        pass

    def writeLayerToFile(self, output, previousLayerFile=None, pp=False):
        data = self.json
        if previousLayerFile is not None and previousLayerFile.exists():
            data = layerModelDiff(jsonLoadFile(previousLayerFile), self.json)
        jsonWriteFile(output, data, pp=pp)

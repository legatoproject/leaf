'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from enum import IntEnum, unique

from leaf.core.jsonutils import (jsonLoadFile, jsonWriteFile, layerModelDiff,
                                 layerModelUpdate, JsonObject)


@unique
class Scope(IntEnum):
    LEAF = 0
    USER = 1
    WORKSPACE = 2
    PROFILE = 3
    PACKAGE = 4


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

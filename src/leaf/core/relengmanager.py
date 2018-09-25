'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from leaf.constants import JsonConstants
from leaf.core.packagemanager import LoggerManager
from leaf.model.package import LeafArtifact, Manifest
from leaf.utils import computeHash, jsonLoadFile, jsonWriteFile, openOutputTarFile


class RelengManager(LoggerManager):
    '''
    Methods needed for releng, ie generate packages and maintain repository
    '''

    def __init__(self, verbosity, nonInteractive):
        LoggerManager.__init__(self, verbosity, nonInteractive)

    def _getNowDate(self):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def _updateManifest(self, manifestFile, updateDate=None):
        model = Manifest(jsonLoadFile(manifestFile))
        modelUpdated = False
        if updateDate is True or (updateDate is None and model.getDate() is None):
            self.logger.printDefault("Update date for %s" % manifestFile)
            model.getNodeInfo()[JsonConstants.INFO_DATE] = self._getNowDate()
            modelUpdated = True

        if modelUpdated:
            jsonWriteFile(manifestFile, model.json, pp=True)
        return model

    def pack(self, manifestFile, outputFile, updateDate=None):
        '''
        Create a leaf artifact from given the manifest.
        if the output file ands with .json, a *manifest only* package will be generated.
        Output file can ends with tar.[gz,xz,bz2] of json
        '''
        manifest = self._updateManifest(manifestFile, updateDate)

        self.logger.printDefault("Found:", manifest.getIdentifier())
        self.logger.printDefault(
            "Create tar:", manifestFile, "-->", outputFile)
        with openOutputTarFile(outputFile) as tf:
            for file in manifestFile.parent.glob('*'):
                tf.add(str(file),
                       str(file.relative_to(manifestFile.parent)))

    def index(self, outputFile, artifacts, name=None, description=None):
        '''
        Create an index.json referencing all given artifacts
        '''
        infoNode = OrderedDict()
        if name is not None:
            infoNode[JsonConstants.REMOTE_NAME] = name
        if description is not None:
            infoNode[JsonConstants.REMOTE_DESCRIPTION] = description
        infoNode[JsonConstants.REMOTE_DATE] = self._getNowDate()

        rootNode = OrderedDict()
        rootNode[JsonConstants.INFO] = infoNode

        hashMap = {}
        packagesNode = []
        rootNode[JsonConstants.REMOTE_PACKAGES] = packagesNode
        for a in artifacts:
            la = LeafArtifact(a)
            pi = la.getIdentifier()
            hash = computeHash(a)
            if pi in hashMap:
                if hash != hashMap[pi]:
                    raise ValueError(
                        "Artifact %s has multiple artifacts for same version" % pi)
                self.logger.printDefault("Artifact already present, skip:", pi)
            else:
                hashMap[pi] = hash
                self.logger.printDefault("Found:", pi)
                fileNode = OrderedDict()
                fileNode[JsonConstants.REMOTE_PACKAGE_FILE] = str(
                    Path(a).relative_to(outputFile.parent))
                fileNode[JsonConstants.REMOTE_PACKAGE_HASH] = str(hash)
                fileNode[JsonConstants.REMOTE_PACKAGE_SIZE] = a.stat().st_size
                fileNode[JsonConstants.INFO] = la.getNodeInfo()
                packagesNode.append(fileNode)

        jsonWriteFile(outputFile, rootNode, pp=True)
        self.logger.printDefault("Index created:", outputFile)

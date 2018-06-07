'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from collections import OrderedDict
from datetime import datetime
from leaf.constants import JsonConstants
from leaf.utils import jsonLoadFile, openOutputTarFile, computeSha1sum,\
    jsonWriteFile
from pathlib import Path

from leaf.model.package import Manifest, LeafArtifact


class RelengManager():
    '''
    Methods needed for releng, ie generate packages and maintain repository
    '''

    def __init__(self, logger):
        self.logger = logger

    def pack(self, manifestFile, outputFile):
        '''
        Create a leaf artifact from given the manifest.
        if the output file ands with .json, a *manifest only* package will be generated.
        Output file can ends with tar.[gz,xz,bz2] of json
        '''
        manifest = Manifest(jsonLoadFile(manifestFile))
        self.logger.printDefault("Found:", manifest.getIdentifier())
        self.logger.printDefault(
            "Create tar:", manifestFile, "-->", outputFile)
        with openOutputTarFile(outputFile) as tf:
            for file in manifestFile.parent.glob('*'):
                tf.add(str(file),
                       str(file.relative_to(manifestFile.parent)))

    def index(self, outputFile, artifacts, name=None, description=None, composites=[]):
        '''
        Create an index.json referencing all given artifacts
        '''
        infoNode = OrderedDict()
        if name is not None:
            infoNode[JsonConstants.REMOTE_NAME] = name
        if description is not None:
            infoNode[JsonConstants.REMOTE_DESCRIPTION] = description
        infoNode[JsonConstants.REMOTE_DATE] = str(datetime.utcnow())

        rootNode = OrderedDict()
        rootNode[JsonConstants.INFO] = infoNode
        if composites is not None and len(composites) > 0:
            rootNode[JsonConstants.REMOTE_COMPOSITE] = composites

        packagesNode = []
        rootNode[JsonConstants.REMOTE_PACKAGES] = packagesNode
        for a in artifacts:
            la = LeafArtifact(a)
            self.logger.printDefault("Found:", la.getIdentifier())
            fileNode = OrderedDict()
            fileNode[JsonConstants.REMOTE_PACKAGE_FILE] = str(
                Path(a).relative_to(outputFile.parent))
            fileNode[JsonConstants.REMOTE_PACKAGE_SHA1SUM] = str(
                computeSha1sum(a))
            fileNode[JsonConstants.REMOTE_PACKAGE_SIZE] = a.stat().st_size
            fileNode[JsonConstants.INFO] = la.getNodeInfo()
            packagesNode.append(fileNode)

        jsonWriteFile(outputFile, rootNode, pp=True)
        self.logger.printDefault("Index created:", outputFile)

'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import platform
from pathlib import Path

from leaf import __version__
from leaf.core.constants import LeafFiles, LeafSettings
from leaf.core.error import LeafException, UserCancelException
from leaf.core.logger import TextLogger
from leaf.rendering.renderer.error import HintsRenderer, LeafExceptionRenderer
from leaf.rendering.renderer.question import QuestionRenderer
from leaf.rendering.theme import ThemeManager
from leaf.model.config import UserConfiguration
from leaf.model.environment import Environment


class ConfigurationManager():
    def __init__(self):
        '''
        Constructor
        '''
        self.configurationFolder = Path(LeafSettings.CONFIG_FOLDER.value)
        self.cacheFolder = Path(LeafSettings.CACHE_FOLDER.value)
        # Ensure folders exist
        if not self.configurationFolder.is_dir():
            self.configurationFolder.mkdir(parents=True)
        if not self.cacheFolder.is_dir():
            self.cacheFolder.mkdir(parents=True)

    def initLeafSettings(self):
        userEnvMap = self.readConfiguration().getEnvMap()
        for s in LeafSettings.values():
            if s.key in userEnvMap:
                s.value = userEnvMap[s.key]

    def getConfigurationFile(self, filename, checkExists=False):
        '''
        Return the path of a configuration file.
        If checkExists arg is True and the file does not exists, returns None
        '''
        out = self.configurationFolder / filename
        if checkExists and not out.exists():
            return None
        return out

    def readConfiguration(self):
        '''
        Read the configuration if it exists, else return the the default configuration
        '''
        return UserConfiguration(
            LeafFiles.ETC_PREFIX / LeafFiles.CONFIG_FILENAME,
            self.getConfigurationFile(LeafFiles.CONFIG_FILENAME))

    def writeConfiguration(self, usrc):
        '''
        Write the given configuration
        '''
        usrc.writeLayerToFile(
            self.getConfigurationFile(LeafFiles.CONFIG_FILENAME),
            previousLayerFile=LeafFiles.ETC_PREFIX / LeafFiles.CONFIG_FILENAME,
            pp=True)

    def getBuiltinEnvironment(self):
        out = Environment("Leaf built-in variables")
        out.env.append(("LEAF_VERSION", str(__version__)))
        out.env.append(("LEAF_PLATFORM_SYSTEM", platform.system()))
        out.env.append(("LEAF_PLATFORM_MACHINE", platform.machine()))
        out.env.append(("LEAF_PLATFORM_RELEASE", platform.release()))
        return out

    def getUserEnvironment(self):
        return self.readConfiguration().getEnvironment()

    def updateUserEnv(self, setMap=None, unsetList=None):
        usrc = self.readConfiguration()
        usrc.updateEnv(setMap, unsetList)
        self.writeConfiguration(usrc)


class LoggerManager(ConfigurationManager):

    def __init__(self):
        ConfigurationManager.__init__(self)
        # If the theme file does not exists, try to find a skeleton
        self.themeManager = ThemeManager(
            self.getConfigurationFile(LeafFiles.THEMES_FILENAME, checkExists=True) or LeafFiles.ETC_PREFIX / LeafFiles.THEMES_FILENAME)
        self.logger = TextLogger()

    def printHints(self, *hints):
        tr = HintsRenderer()
        tr.extend(hints)
        self.printRenderer(tr)

    def printException(self, ex):
        if isinstance(ex, LeafException):
            self.printRenderer(LeafExceptionRenderer(ex))
        else:
            self.logger.printError(str(ex))

    def printRenderer(self, renderer, verbosity=None):
        renderer.verbosity = verbosity if verbosity is not None else self.logger.verbosity
        renderer.tm = self.themeManager
        renderer.print()

    def confirm(self, question="Do you want to continue?", raiseOnDecline=False):
        out = None
        while out is None:
            self.printRenderer(QuestionRenderer(question + ' (Y/n)'))
            if LeafSettings.NON_INTERACTIVE.as_boolean():
                out = True
            else:
                answer = input().strip()
                if answer == '' or answer.lower() == 'y':
                    out = True
                elif answer.lower() == 'n':
                    out = False
        if not out and raiseOnDecline:
            raise UserCancelException()
        return out

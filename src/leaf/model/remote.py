'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.constants import JsonConstants
from leaf.core.error import LeafException
from leaf.model.base import JsonObject


class Remote(JsonObject):

    def __init__(self, alias, json, content=None):
        JsonObject.__init__(self, json)
        self.alias = alias
        self.content = content

    def isEnabled(self):
        return self.jsonget(JsonConstants.CONFIG_REMOTE_ENABLED, True)

    def getGpgKey(self):
        return self.jsonget(JsonConstants.CONFIG_REMOTE_GPGKEY)

    def setEnabled(self, enabled):
        self.json[JsonConstants.CONFIG_REMOTE_ENABLED] = enabled

    def getUrl(self):
        return self.jsonget(JsonConstants.CONFIG_REMOTE_URL, mandatory=True)

    def isFetched(self):
        return self.content is not None

    def getInfo(self):
        if not self.isFetched():
            raise LeafException("Remote is not fetched")
        return JsonObject(self.content).jsonget(JsonConstants.INFO, default={})

    def getInfoName(self):
        return self.getInfo().get(JsonConstants.REMOTE_NAME)

    def getInfoDescription(self):
        return self.getInfo().get(JsonConstants.REMOTE_DESCRIPTION)

    def getInfoDate(self):
        return self.getInfo().get(JsonConstants.REMOTE_DATE)

    def __str__(self):
        return self.alias

    def getAvailablePackageList(self):
        if not self.isFetched():
            raise LeafException("Remote is not fetched")
        return JsonObject(self.content).jsonget(JsonConstants.REMOTE_PACKAGES, [])

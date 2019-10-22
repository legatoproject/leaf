"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from functools import total_ordering

from leaf.core.constants import JsonConstants
from leaf.core.download import PRIORITIES_RANGE, get_url_priority
from leaf.core.error import LeafException
from leaf.core.jsonutils import JsonObject
from leaf.model.package import AvailablePackage


@total_ordering
class Remote(JsonObject):
    def __init__(self, alias, json, content=None):
        JsonObject.__init__(self, json)
        self.__alias = alias
        self.__content = content

    @property
    def alias(self):
        return self.__alias

    @property
    def content(self):
        return self.__content

    @content.setter
    def content(self, content):
        self.__content = content

    @property
    def enabled(self):
        return self.jsonget(JsonConstants.CONFIG_REMOTE_ENABLED, True)

    @enabled.setter
    def enabled(self, enabled):
        self.json[JsonConstants.CONFIG_REMOTE_ENABLED] = enabled

    @property
    def gpg_key(self):
        return self.jsonget(JsonConstants.CONFIG_REMOTE_GPGKEY)

    @property
    def url(self):
        return self.jsonget(JsonConstants.CONFIG_REMOTE_URL, mandatory=True)

    @property
    def priority(self):
        out = self.jsonget(JsonConstants.CONFIG_REMOTE_PRIORITY)
        return out if out in PRIORITIES_RANGE else get_url_priority(self.url)

    @property
    def is_fetched(self):
        return self.content is not None

    @property
    def info_node(self):
        if not self.is_fetched:
            raise LeafException("Remote is not fetched")
        return JsonObject(self.content).jsonget(JsonConstants.INFO, default={})

    @property
    def info_name(self):
        return self.info_node.get(JsonConstants.REMOTE_NAME)

    @property
    def info_description(self):
        return self.info_node.get(JsonConstants.REMOTE_DESCRIPTION)

    @property
    def info_date(self):
        return self.info_node.get(JsonConstants.REMOTE_DATE)

    def __str__(self):
        return self.alias

    @property
    def available_packages(self) -> list:
        if not self.is_fetched:
            raise LeafException("Remote is not fetched")
        out = []
        for json in JsonObject(self.content).jsonget(JsonConstants.REMOTE_PACKAGES, []):
            ap = AvailablePackage(json, remote=self)
            out.append(ap)
        return out

    def __lt__(self, other):
        if not isinstance(other, Remote):
            return NotImplemented
        return self.priority < other.priority

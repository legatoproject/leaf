"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from pkg_resources import get_distribution

__title__ = "leaf"
__version__ = get_distribution(__title__).version
__short_version__ = ".".join(__version__.split(".")[:2])
__author__ = "Sierra Wireless"
__license__ = "Mozilla Public License Version 2.0"
__license_url__ = "https://www.mozilla.org/en-US/MPL/2.0/"
__copyright__ = "Copyright Sierra Wireless. All rights reserved."

__help_description__ = """{copyright}

  Licensed under the {license}
  {license_url}

  Leaf is part of the Legato Project, https://legato.io/

""".format(
    copyright=__copyright__, license=__license__, license_url=__license_url__
)

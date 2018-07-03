'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from pkg_resources import get_distribution

__title__ = 'leaf'
__version__ = get_distribution(__title__).version
__short_version__ = '.'.join(__version__.split('.')[:2])
__author__ = 'Sierra Wireless'
__license__ = 'Mozilla Public License Version 2.0'
__license_url__ = 'https://www.mozilla.org/en-US/MPL/2.0/'
__copyright__ = 'Copyright 2018 Sierra Wireless. All rights reserved.'

__help_description__ = __copyright__ + '''

  Licensed under the ''' + __license__ + '''
  ''' + __license_url__ + '''  

  Leaf is part of the Legato Project, http://legato.io/

'''

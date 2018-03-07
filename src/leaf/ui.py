'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from leaf.model import Manifest


def askYesNo(logger, message, default=None):
    label = " (yes/no)"
    if default == True:
        label = " (YES/no)"
    elif default == False:
        label = " (yes/NO)"
    while True:
        logger.printDefault(message + label + " ")
        answer = input().strip()
        if answer == "":
            if default == True:
                answer = 'y'
            elif default == False:
                answer = 'n'
        if answer.lower() == 'y' or answer.lower() == 'yes':
            return True
        if answer.lower() == 'n' or answer.lower() == 'no':
            return False


def filterPackageList(content, keywords=None, modules=None, sort=True):
    '''
    Filter a list of packages given optional criteria
    '''
    out = list(content)

    def my_filter(p):
        out = True
        if modules is not None and len(modules) > 0:
            out = False
            if p.getSupportedModules() is not None:
                for m in modules:
                    if m.lower() in map(str.lower, p.getSupportedModules()):
                        out = True
                        break
        if out and keywords is not None and len(keywords) > 0:
            out = False
            for k in keywords:
                k = k.lower()
                if k in str(p.getIdentifier()).lower():
                    out = True
                    break
                if p.getDescription() is not None and k in p.getDescription().lower():
                    out = True
                    break
        return out
    out = filter(my_filter, out)
    if sort:
        out = sorted(out, key=Manifest.getIdentifier)
    return out
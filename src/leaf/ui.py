'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''


def askYesNo(logger, message, default=None):
    label = " (yes/no)"
    if default == True:
        label = " (YES/no)"
    elif default == False:
        label = " (yes/NO)"
    while True:
        logger.printMessage(message + label + " ")
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

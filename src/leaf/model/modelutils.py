'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''


from collections import OrderedDict


def layerModelUpdate(left, right):
    '''
    Update the *left* model with values from *right*
    Both left & right have to be dict objects
    '''
    if not isinstance(left, dict):
        raise ValueError("Problem with json layer")
    if not isinstance(right, dict):
        raise ValueError("Problem with json layer")

    for key in list(left.keys()):
        if key in right:
            if right[key] is None:
                # Delete value
                del left[key]
            elif isinstance(left[key], dict) and isinstance(right[key], dict):
                # Reccursive update
                layerModelUpdate(left[key], right[key])
            else:
                # Replace
                left[key] = right[key]
    for key in right.keys():
        if key not in left and right[key] is not None:
            # Add it
            left[key] = right[key]
    return left


def layerModelDiff(left, right):
    '''
    Compute the difference between the *left* and *right* model
    Both left & right have to be dict objects
    '''
    if not isinstance(left, dict):
        raise ValueError("Problem with json layer")
    if not isinstance(right, dict):
        raise ValueError("Problem with json layer")
    # Special case, diff is empty
    if left == right:
        return OrderedDict()

    out = OrderedDict()
    for key in left.keys():
        if key in right:
            if left[key] == right[key]:
                # Same value, do nothing
                pass
            elif isinstance(left[key], dict) and isinstance(right[key], dict):
                # Recursive diff
                out[key] = layerModelDiff(left[key], right[key])
            else:
                # Value has been updated
                out[key] = right[key]
        else:
            # Delete value
            out[key] = None
    for key in right.keys():
        if key not in left:
            # New value
            out[key] = right[key]

    return out

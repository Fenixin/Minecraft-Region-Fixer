"""
Useful utility functions for handling large NBT structures elegantly and
Pythonically.
"""

# Yes, yes, I know. Fix it if you like.
from nbt import *

def unpack_nbt(tag):
    """
    Unpack an NBT tag into a native Python data structure.
    """

    if isinstance(tag, TAG_List):
        return [unpack_nbt(i) for i in tag.tags]
    elif isinstance(tag, TAG_Compound):
        return dict((i.name, unpack_nbt(i)) for i in tag.tags)
    else:
        return tag.value

def pack_nbt(s):
    """
    Pack a native Python data structure into an NBT tag. Only the following
    structures and types are supported:

     * int
     * float
     * str
     * unicode
     * dict

    Additionally, arbitrary iterables are supported.

    Packing is not lossless. In order to avoid data loss, TAG_Long and
    TAG_Double are preferred over the less precise numerical formats.

    Lists and tuples may become dicts on unpacking if they were not homogenous
    during packing, as a side-effect of NBT's format. Nothing can be done
    about this.

    Only strings are supported as keys for dicts and other mapping types. If
    your keys are not strings, they will be coerced. (Resistance is futile.)
    """

    if isinstance(s, int):
        return TAG_Long(s)
    elif isinstance(s, float):
        return TAG_Double(s)
    elif isinstance(s, (str, unicode)):
        return TAG_String(s)
    elif isinstance(s, dict):
        tag = TAG_Compound()
        for k, v in s:
            v = pack_nbt(v)
            v.name = str(k)
            tag.tags.append(v)
        return tag
    elif hasattr(s, "__iter__"):
        # We arrive at a slight quandry. NBT lists must be homogenous, unlike
        # Python lists. NBT compounds work, but require unique names for every
        # entry. On the plus side, this technique should work for arbitrary
        # iterables as well.
        tags = [pack_nbt(i) for i in s]
        t = type(tags[0])
        # If we're homogenous...
        if all(t == type(i) for i in tags):
            tag = TAG_List(type=t)
            tag.tags = tags
        else:
            tag = TAG_Compound()
            for i, item in enumerate(tags):
                item.name = str(i)
            tag.tags = tags
        return tag
    else:
        raise ValueError("Couldn't serialise type %s!" % type(s))

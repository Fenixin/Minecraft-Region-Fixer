"""
Utility methods for handling oddities in character encoding encountered
when parsing and writing JVM ClassFiles or object serialization archives.

MUTF-8 is the same as CESU-8, but with different encoding for 0x00 bytes.

.. note::

    http://bugs.python.org/issue2857 was an attempt in 2008 to get support
    for MUTF-8/CESU-8 into the python core.
"""


try:
    from mutf8.cmutf8 import decode_modified_utf8, encode_modified_utf8
except ImportError:
    from mutf8.mutf8 import decode_modified_utf8, encode_modified_utf8


# Shut up linters.
ALL_IMPORTS = [decode_modified_utf8, encode_modified_utf8]

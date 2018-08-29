__all__ = ["nbt", "world", "region", "chunk"]
from . import *

# Documentation only automatically includes functions specified in __all__.
# If you add more functions, please manually include them in doc/index.rst.

VERSION = (1, 5, 0)
"""NBT version as tuple. Note that the major and minor revision number are 
always present, but the patch identifier (the 3rd number) is only used in 1.4."""

def _get_version():
    """Return the NBT version as string."""
    return ".".join([str(v) for v in VERSION])

__all__ = ["nbt", "world", "region", "chunk"]
from . import *

# Documentation only automatically includes functions specified in __all__.
# If you add more functions, please manually include them in doc/index.rst.

VERSION = (1, 3)
"""NBT version as tuple. The version currently only contains major and minor 
revision number, but not (yet) patch and build identifiers."""

def _get_version():
	"""Return the NBT version as string."""
	return ".".join([str(v) for v in VERSION])

__all__ = ["chunk", "region", "world", "nbt"]
from . import *

VERSION = (1, 2)

def _get_version():
	return ".".join(VERSION)

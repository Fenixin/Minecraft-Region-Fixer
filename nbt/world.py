"""
Handles a Minecraft world save using either the Anvil or McRegion format.
"""

import os
import glob
import re

from . import region
from . import chunk
from .region import InconceivedChunk


class UnknownWorldFormat(Exception):
    """Unknown or invalid world folder."""

    def __init__(self, msg=""):
        self.msg = msg


class _BaseWorldFolder(object):
    """
    Abstract class, representing either a McRegion or Anvil world folder.
    This class will use either Anvil or McRegion, with Anvil the preferred format.
    Simply calling WorldFolder() will do this automatically.
    """
    type = "Generic"

    def __init__(self, world_folder):
        """Initialize a WorldFolder."""
        self.worldfolder = world_folder
        self.regionfiles = {}
        self.regions = {}
        self.chunks = None
        # os.listdir triggers an OSError for non-existant directories or permission errors.
        # This is needed, because glob.glob silently returns no files.
        os.listdir(world_folder)
        self.set_regionfiles(self.get_filenames())

    def get_filenames(self):
        # Warning: glob returns a empty list if the directory is unreadable, without raising an Exception
        return list(glob.glob(os.path.join(self.worldfolder, 'region', 'r.*.*.' + self.extension)))

    def set_regionfiles(self, filenames):
        """
        This method directly sets the region files for this instance to use.
        It assumes the filenames are in the form r.<x-digit>.<z-digit>.<extension>
        """
        for filename in filenames:
            # Assume that filenames have the name r.<x-digit>.<z-digit>.<extension>
            m = re.match(r"r.(\-?\d+).(\-?\d+)." + self.extension, os.path.basename(filename))
            if m:
                x = int(m.group(1))
                z = int(m.group(2))
            else:
                # Only raised if a .mca of .mcr file exists which does not comply to the
                #  r.<x-digit>.<z-digit>.<extension> filename format. This may raise false
                # errors if a copy is made, e.g. "r.0.-1 copy.mca". If this is an issue, override
                # get_filenames(). In most cases, it is an error, and we like to raise that.
                # Changed, no longer raise error, because we want to continue the loop.
                # raise UnknownWorldFormat("Unrecognized filename format %s" % os.path.basename(filename))
                # TODO: log to stderr using logging facility.
                pass
            self.regionfiles[(x, z)] = filename

    def nonempty(self):
        """Return True is the world is non-empty."""
        return len(self.regionfiles) > 0

    def get_regionfiles(self):
        """Return a list of full path of all region files."""
        return list(self.regionfiles.values())

    def get_region(self, x, z):
        """Get a region using x,z coordinates of a region. Cache results."""
        if (x, z) not in self.regions:
            if (x, z) in self.regionfiles:
                self.regions[(x, z)] = region.RegionFile(self.regionfiles[(x, z)])
            else:
                # Return an empty RegionFile object
                # TODO: this does not yet allow for saving of the region file
                self.regions[(x, z)] = region.RegionFile()
        return self.regions[(x, z)]

    def iter_regions(self):
        for x, z in self.regionfiles.keys():
            yield self.get_region(x, z)

    def iter_nbt(self):
        """
        Return an iterable list of all NBT. Use this function if you only
        want to loop through the chunks once, and don't need the block or data arrays.
        """
        # TODO: Implement BoundingBox
        # TODO: Implement sort order
        for region in self.iter_regions():
            for c in region.iter_chunks():
                yield c

    def iter_chunks(self):
        """
        Return an iterable list of all chunks. Use this function if you only
        want to loop through the chunks once or have a very large world.
        Use get_chunks() if you access the chunk list frequently and want to cache
        the results. Use iter_nbt() if you are concerned about speed and don't want
        to parse the block data.
        """
        # TODO: Implement BoundingBox
        # TODO: Implement sort order
        for c in self.iter_nbt():
            yield self.chunkclass(c)

    def get_nbt(self, x, z):
        """
        Return a NBT specified by the chunk coordinates x,z. Raise InconceivedChunk
        if the NBT file is not yet generated. To get a Chunk object, use get_chunk.
        """
        rx, x = divmod(x, 32)
        rz, z = divmod(z, 32)
        nbt = self.get_region(rx, rz).get_chunk(x, z)
        if nbt == None:
            raise InconceivedChunk("Chunk %s,%s not present in world" % (32 * rx + x, 32 * rz + z))
        return nbt

    def set_nbt(self, x, z, nbt):
        """
        Set a chunk. Overrides the NBT if it already existed. If the NBT did not exists,
        adds it to the Regionfile. May create a new Regionfile if that did not exist yet.
        nbt must be a nbt.NBTFile instance, not a Chunk or regular TAG_Compound object.
        """
        raise NotImplemented()
        # TODO: implement

    def get_chunk(self, x, z):
        """
        Return a chunk specified by the chunk coordinates x,z. Raise InconceivedChunk
        if the chunk is not yet generated. To get the raw NBT data, use get_nbt.
        """
        return self.chunkclass(self.get_nbt(x, z))

    def get_chunks(self, boundingbox=None):
        """
        Return a list of all chunks. Use this function if you access the chunk
        list frequently and want to cache the result.
        Use iter_chunks() if you only want to loop through the chunks once or have a
        very large world.
        """
        if self.chunks == None:
            self.chunks = list(self.iter_chunks())
        return self.chunks

    def chunk_count(self):
        """Return a count of the chunks in this world folder."""
        c = 0
        for r in self.iter_regions():
            c += r.chunk_count()
        return c

    def get_boundingbox(self):
        """
        Return minimum and maximum x and z coordinates of the chunks that
        make up this world save
        """
        b = BoundingBox()
        for rx, rz in self.regionfiles.keys():
            region = self.get_region(rx, rz)
            rx, rz = 32 * rx, 32 * rz
            for cc in region.get_chunk_coords():
                x, z = (rx + cc['x'], rz + cc['z'])
                b.expand(x, None, z)
        return b

    def cache_test(self):
        """
        Debug routine: loop through all chunks, fetch them again by coordinates,
        and check if the same object is returned.
        """
        # TODO: make sure this test succeeds (at least True,True,False, preferable True,True,True)
        # TODO: Move this function to test class.
        for rx, rz in self.regionfiles.keys():
            region = self.get_region(rx, rz)
            rx, rz = 32 * rx, 32 * rz
            for cc in region.get_chunk_coords():
                x, z = (rx + cc['x'], rz + cc['z'])
                c1 = self.chunkclass(region.get_chunk(cc['x'], cc['z']))
                c2 = self.get_chunk(x, z)
                correct_coords = (c2.get_coords() == (x, z))
                is_comparable = (c1 == c2)  # test __eq__ function
                is_equal = (id(c1) == id(c2))  # test if they point to the same memory location
                # DEBUG (prints a tuple)
                print((x, z, c1, c2, correct_coords, is_comparable, is_equal))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.worldfolder)


class McRegionWorldFolder(_BaseWorldFolder):
    """Represents a world save using the old McRegion format."""
    type = "McRegion"
    extension = 'mcr'
    chunkclass = chunk.Chunk
    # chunkclass = chunk.McRegionChunk  # TODO: change to McRegionChunk when done


class AnvilWorldFolder(_BaseWorldFolder):
    """Represents a world save using the new Anvil format."""
    type = "Anvil"
    extension = 'mca'
    chunkclass = chunk.Chunk
    # chunkclass = chunk.AnvilChunk  # TODO: change to AnvilChunk when done


class _WorldFolderFactory():
    """Factory class: instantiate the subclassses in order, and the first instance 
    whose nonempty() method returns True is returned. If no nonempty() returns True,
    a UnknownWorldFormat exception is raised."""

    def __init__(self, subclasses):
        self.subclasses = subclasses

    def __call__(self, *args, **kwargs):
        for cls in self.subclasses:
            wf = cls(*args, **kwargs)
            if wf.nonempty():  # Check if the world is non-empty
                return wf
        raise UnknownWorldFormat("Empty world or unknown format: %r" % world_folder)


WorldFolder = _WorldFolderFactory([AnvilWorldFolder, McRegionWorldFolder])
"""
Factory instance that returns a AnvilWorldFolder or McRegionWorldFolder
instance, or raise a UnknownWorldFormat.
"""


class BoundingBox(object):
    """A bounding box of x,y,z coordinates."""

    def __init__(self, minx=None, maxx=None, miny=None, maxy=None, minz=None, maxz=None):
        self.minx, self.maxx = minx, maxx
        self.miny, self.maxy = miny, maxy
        self.minz, self.maxz = minz, maxz

    def expand(self, x, y, z):
        """
        Expands the bounding
        """
        if x != None:
            if self.minx is None or x < self.minx:
                self.minx = x
            if self.maxx is None or x > self.maxx:
                self.maxx = x
        if y != None:
            if self.miny is None or y < self.miny:
                self.miny = y
            if self.maxy is None or y > self.maxy:
                self.maxy = y
        if z != None:
            if self.minz is None or z < self.minz:
                self.minz = z
            if self.maxz is None or z > self.maxz:
                self.maxz = z

    def lenx(self):
        return self.maxx - self.minx + 1

    def leny(self):
        return self.maxy - self.miny + 1

    def lenz(self):
        return self.maxz - self.minz + 1

    def __repr__(self):
        return "%s(%s,%s,%s,%s,%s,%s)" % (self.__class__.__name__, self.minx, self.maxx, self.miny, self.maxy, self.minz, self.maxz)

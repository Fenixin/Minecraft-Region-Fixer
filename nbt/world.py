"""Handle a world folder, containing """

import os, glob, re
from . import region
from . import chunk

class Format(object):
	# format constants
	INVALID     = -1  # Unknown or invalid world folder format
	ALPHA       = 1   # Unsupported
	MCREGION    = 2   # "Beta" file format
	ANVIL       = 3   # Anvil file format, introduced in Minecraft 1.2


class UnknownWorldFormat(Exception):
	"""Unknown or invalid world folder"""
	def __init__(self, msg):
		self.msg = msg

class WorldFolder(object):
	def __init__(self, world_folder, format=None):
		self.worldfolder = world_folder
		self.format = format
		os.listdir(world_folder) # Trigger OSError for non-existant directories or permission errors.
		mcregion_fn  = list(glob.glob(os.path.join(world_folder,'region','r.*.*.mcr')))
		anvil_fn     = list(glob.glob(os.path.join(world_folder,'region','r.*.*.mca')))
		if self.format == None:
			if (len(anvil_fn) > 0):
				self.format = Format.ANVIL
				regionfiles = anvil_fn
			elif (len(mcregion_fn) > 0):
				self.format = Format.MCREGION
				regionfiles = mcregion_fn
			else:
				raise UnknownWorldFormat("Empty world or not a McRegion or Anvil format")
		elif self.format == Format.ANVIL:
			if len(anvil_fn) == 0:
				raise UnknownWorldFormat("Empty world or not a Anvil format")
			regionfiles = anvil_fn
		elif self.format == Format.MCREGION:
			if len(mcregion_fn) == 0:
				raise UnknownWorldFormat("Empty world or not a McRegion format")
			regionfiles = mcregion_fn
		else:
			raise UnknownWorldFormat("Unsupported world format")
		self.regionfiles = {}
		for filename in regionfiles:
			m = re.match(r"r.(\-?\d+).(\-?\d+).mc[ra]", os.path.basename(filename))
			if m:
				x = int(m.group(1))
				z = int(m.group(2))
			else:
				raise UnknownWorldFormat("Unrecognized filename format %s" % os.path.basename(filename))
			self.regionfiles[(x,z)] = filename
		self.regions     = {}
		self.chunks      = None

	def get_regionfiles():
		"""return a list of full path with region files"""
		return self.regionfiles.values()
	
	def get_region(self, x,z):
		"""Get a region using x,z coordinates of a region. Cache results."""
		if (x,z) not in self.regions:
			if (x,z) in self.regionfiles:
				self.regions[(x,z)] = region.RegionFile(self.regionfiles[(x,z)])
			else:
				# Return an empty RegionFile object
				# TODO: this does not yet allow for saving of the region file
				self.regions[(x,z)] = region.RegionFile()
		return self.regions[(x,z)]
	
	def iter_regions(self):
		for x,z in self.regionfiles.keys():
			yield self.get_region(x,z)

	def iter_chunks(self):
		"""Returns an iterable list of all chunks. Use this function if you only 
		want to loop through the chunks once or have a very large world."""
		# TODO: Implement BoundingBox
		# TODO: Implement sort order
		for region in self.iter_regions():
			for c in region.iter_chunks():
				yield chunk.Chunk(c)

	def get_chunk(self,x,z):
		"""Return a chunk specified by the chunk coordinates x,z."""
		# TODO: Implement (calculate region filename from x,z, see if file exists.)
		rx,x = divmod(x,32)
		rz,z = divmod(z,32)
		return chunk.Chunk(self.get_region(rx,rz).get_chunk(x,z))
	
	def get_chunks(self, boundingbox=None):
		"""Returns a list of all chunks. Use this function if you access the chunk
		list frequently and want to cache the result."""
		if self.chunks == None:
			self.chunks = list(self.iter_chunks())
		return self.chunks
	
	def chunk_count(self):
		c = 0
		for r in self.iter_regions():
			c += r.chunk_count()
		return c 
	
	def get_boundingbox(self):
		"""Return minimum and maximum x and z coordinates of the chunks."""
		b = BoundingBox()
		for rx,rz in self.regionfiles.keys():
			region = self.get_region(rx,rz)
			rx,rz = 32*rx,32*rz
			for cc in region.get_chunk_coords():
				x,z = (rx+cc['x'],rz+cc['z'])
				b.expand(x,None,z)
		return b
	
	def cache_test(self):
		"""Debug routine: loop through all chunks, fetch them again by coordinates, and check if the same object is returned."""
		# TODO: make sure this test succeeds (at least True,True,False, preferable True,True,True)
		# TODO: Move this function to test class.
		for rx,rz in self.regionfiles.keys():
			region = self.get_region(rx,rz)
			rx,rz = 32*rx,32*rz
			for cc in region.get_chunk_coords():
				x,z = (rx+cc['x'],rz+cc['z'])
				c1 = chunk.Chunk(region.get_chunk(cc['x'],cc['z']))
				c2 = self.get_chunk(x,z)
				correct_coords = (c2.get_coords() == (x,z))
				is_comparable = (c1 == c2) # test __eq__ function
				is_equal = (c1 == c2) # test if id(c1) == id(c2), thus they point to the same memory location
				print x,z,c1,c2,correct_coords,is_comparable,is_equal
	
	def __str__(self):
		return "%s(%s,%s)" % (self.__class__.__name__,self.worldfolder, self.format)


class BoundingBox(object):
	"""A bounding box of x,y,z coordinates"""
	def __init__(self,minx=None, maxx=None, miny=None, maxy=None, minz=None, maxz=None):
		self.minx,self.maxx = minx, maxx
		self.miny,self.maxy = miny, maxy
		self.minz,self.maxz = minz, maxz
	def expand(self,x,y,z):
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
		return self.maxx-self.minx+1
	def leny(self):
		return self.maxy-self.miny+1
	def lenz(self):
		return self.maxz-self.minz+1
	def __str__(self):
		return "%s(%s,%s,%s,%s,%s,%s)" % (self.__class__.__name__,self.minx,self.maxx,
				self.miny,self.maxy,self.minz,self.maxz)

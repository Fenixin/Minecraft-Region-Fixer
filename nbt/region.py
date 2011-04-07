from nbt import NBTFile
from chunk import Chunk
from struct import pack, unpack
from gzip import GzipFile
import zlib
from StringIO import StringIO
import math, time, datetime
from os.path import getsize

class RegionHeaderError(Exception):
	"""Error in the header of the region file for a given chunk"""
	def __init__(self, msg):
		self.msg = msg

class ChunkHeaderError(Exception):
	"""Error in the header of a chunk"""
	def __init__(self, msg):
		self.msg = msg

class ChunkDataError(Exception):
	"""Error in the data of a chunk, included the bytes of length and byte version"""
	def __init__(self, msg):
		self.msg = msg


class RegionFile(object):
	"""
	A convenience class for extracting NBT files from the Minecraft Beta Region Format
	"""
	
	def __init__(self, filename=None, fileobj=None):
		if filename:
			self.filename = filename
			self.file = open(filename, 'r+b')
		if fileobj:
			self.file = fileobj
		self.chunks = []
		self.header = {}
		self.chunk_headers = {}
		self.extents = None
		if self.file:
			self.size = getsize(self.filename)
			self.parse_header()
			self.parse_chunk_headers()

	def __del__(self):
		if self.file:
			self.file.close()

	def parse_header(self):
		""" 
		Reads the region header and stores: offset, length and status.
		
		Status is a number representing:
		-2 = Error, chunk inside the region file of the region file
		-1 = Error, chunk partially/completely outside of file
		0  = Ok
		1  = Chunk non-existant yet
		"""
		for index in range(0,4096,4):
			self.file.seek(index)
			offset, length = unpack(">IB", "\0"+self.file.read(4))
			self.file.seek(index + 4096)
			timestamp = unpack(">I", self.file.read(4))
			x = (index/4) % 32
			z = int(index/4)/32
			if offset < 2 and offset != 0: # chunk inside the header of the region file
				status = -2

			elif (offset + length)*4 > self.size: # chunk outside of file
				status = -1

			elif offset == 0: # no created yet
				status = 1

			else:
				status = 0 # everything ok

			self.header[x,z] = (offset, length, timestamp, status)

	def parse_chunk_headers(self):
		for x in range(32):
			for z in range(32):
				offset, region_header_length, timestamp, status = self.header[x,z]

				if status == 1: # chunk not created yet
					length = None
					compression = None
					status = None

				elif status == 0: # there is a chunk!
					self.file.seek(offset*4096) # offset comes in sectors of 4096 bytes
					length = unpack(">I", self.file.read(4))
					length = length[0] # unpack always returns a tuple, even unpacking one element
					compression = unpack(">B",self.file.read(1))
					compression = compression[0]
					# TODO TODO TODO check if the region_file_length and the chunk header length are compatible
					if length == 0: # chunk can't be zero length
						status = -3
					
					else:
						status = 0

				elif status == -1: # error, chunk partially/completely outside the file
					if offset*4096 + 5 < self.size: # if possible read it, just in case it's useful
						self.file.seek(offset*4096) # offset comes in sectors of 4096 bytes
						length = unpack(">I", self.file.read(4))
						length = length[0] # unpack always returns a tuple, even unpacking one element
						compression = unpack(">B",self.file.read(1))
						compression = compression[0]

					else:
						length = None
						compression = None
						status = -1

				elif status == -2: # error, chunk in the header of the region file
					length = None
					compression = None
					status = -2
		
				self.chunk_headers[x, z] = (length, compression, status)


	def locate_free_space(self):
		pass
	
	def get_chunks(self):
		index = 0
		self.file.seek(index)
		chunks = []
		while (index < 4096):
			offset, length = unpack(">IB", "\0"+self.file.read(4))
			if offset:
				x = (index/4) % 32
				z = int(index/4)/32
				chunks.append(Chunk(x,z,length))
			index += 4
		return chunks
	
	@classmethod
	def getchunk(path, x, z):
		pass
		
	def get_timestamp(self, x, z):
		self.file.seek(4096+4*(x+z*32))
		timestamp = unpack(">I",self.file.read(4))

	def get_chunk(self, x, z):
		#read metadata block
		offset, length, timestamp, region_header_status = self.header[x, z]
		if region_header_status == 1:
			return None
			
		elif region_header_status == -2:
			raise RegionHeaderError('The chunk is in the region header')

		elif region_header_status == -1:
			raise RegionHeaderError('The chunk is partially/completely outside the file')

		elif region_header_status == 0:
			length, compression, chunk_header_status = self.chunk_headers[x, z]
			if chunk_header_status == -3: # no chunk can be 0 length!
				raise ChunkHeaderError('The length of the chunk is 0')

			self.file.seek(offset*4*1024 + 5) # offset comes in sectors of 4096 bytes + length bytes + compression byte
			chunk = self.file.read(length-1)

			if (compression == 2):
				try:
					chunk = zlib.decompress(chunk)
				except Exception, e:
					raise ChunkDataError(str(e))
					
				chunk = StringIO(chunk)
				return NBTFile(buffer=chunk) # pass uncompressed
				
			elif (compression == 1):
				chunk = StringIO(chunk)
				try:
					return NBTFile(fileobj=chunk) # pass compressed; will be filtered through Gzip
				except Exception, e:
					raise ChunkDataError(str(e))
					
			else:
				raise ChunkDataError('Unknown chunk compression')
				
		else:
			return None
	
	def write_chunk(self, x, z, nbt_file):
		""" A smart chunk writer that uses extents to trade off between fragmentation and cpu time"""
		data = StringIO()
		nbt_file.write_file(buffer = data) #render to buffer; uncompressed
		
		compressed = zlib.compress(data.getvalue()) #use zlib compression, rather than Gzip
		data = StringIO(compressed)
		
		nsectors = int(math.ceil((data.len+0.001)/4096))
		
		#if it will fit back in it's original slot:
		offset, length, timestamp, status = self.header[x, z]
		pad_end = False
		if status in (1,-1,-2): # don't trust bad headers, write at the end.
			# This chunk hasn't been generated yet, or the header is wrong
			# This chunk should just be appended to the end of the file
			self.file.seek(0,2) # go to the end of the file
			file_length = self.file.tell()-1 # current offset is file length
			total_sectors = file_length/4096
			sector = total_sectors+1
			pad_end = True
		elif status == 0:
			# TODO TODO TODO Check if chunk_status says that the lengths are incompatible (status = -3)
			if nsectors <= length:
				sector = offset
			else:
				#traverse extents to find first-fit
				sector= 2 #start at sector 2, first sector after header
				while 1:
					#check if extent is used, else move foward in extent list by extent length
					# leave this like this or update to use self.header?
					self.file.seek(0)
					found = True
					for intersect_offset, intersect_len in ( (extent_offset, extent_len)
						for extent_offset, extent_len in (unpack(">IB", "\0"+self.file.read(4)) for block in xrange(1024))
							if extent_offset != 0 and ( sector >= extent_offset < (sector+nsectors))):
								#move foward to end of intersect
								sector = intersect_offset + intersect_len
								found = False
								break
					if found:
						break

		#write out chunk to region
		self.file.seek(sector*4096)
		self.file.write(pack(">I", data.len+1)) #length field
		self.file.write(pack(">B", 2)) #compression field
		self.file.write(data.getvalue()) #compressed data
		if pad_end:
			# Write zeros up to the end of the chunk
			self.file.seek((sector+nsectors)*4096-1)
			self.file.write(chr(0))
		
		#seek to header record and write offset and length records
		self.file.seek(4*(x+z*32))
		self.file.write(pack(">IB", sector, nsectors)[1:])
		
		#write timestamp
		self.file.seek(4096+4*(x+z*32))
		timestamp = time.mktime(datetime.datetime.now().timetuple())
		self.file.write(pack(">I", timestamp))

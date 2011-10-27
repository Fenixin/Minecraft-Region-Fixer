#
# For more info of the region file format look:
# http://www.minecraftwiki.net/wiki/Beta_Level_Format
# 

from nbt import NBTFile
from chunk import Chunk
from struct import pack, unpack
from gzip import GzipFile
import zlib
from StringIO import StringIO
import math, time
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
			
		# Some variables and constants
		#
		# Status is a number representing:
		# -4 = Error, the region header length and the chunk length are incompatible
		# -3 = Error, chunk header has a 0 length
		# -2 = Error, chunk inside the header of the region file
		# -1 = Error, chunk partially/completely outside of file
		#  0 = Ok
		#  1 = Chunk non-existant yet

		self.STATUS_CHUNK_MISMATCHED_LENGTHS = -4
		self.STATUS_CHUNK_ZERO_LENGTH = -3
		self.STATUS_CHUNK_IN_HEADER = -2
		self.STATUS_CHUNK_OUT_OF_FILE = -1
		self.STATUS_CHUNK_OK = 0
		self.STATUS_CHUNK_NOT_CREATED = 1
		
		self.chunks = []
		self.header = {}
		self.chunk_headers = {}
		self.extents = None
		if self.file:
			self.size = getsize(self.filename)
			if self.size == 0:
				# Some region files seems to have 0 bytes of size, and
				# Minecraft handle them without problems. Take them 
				# as empty region files.
				for x in range(32):
					for z in range(32):
						self.header[x,z] = (0, 0, 0, self.STATUS_CHUNK_NOT_CREATED)
				self.parse_chunk_headers()
			else:
				self.parse_header()
				self.parse_chunk_headers()


	def __del__(self):
		if self.file:
			self.file.close()

	def parse_header(self):
		""" 
		Reads the region header and stores: offset, length and status.
		
		"""
		for index in range(0,4096,4):
			self.file.seek(index)
			offset, length = unpack(">IB", "\0"+self.file.read(4))
			self.file.seek(index + 4096)
			timestamp = unpack(">I", self.file.read(4))
			x = (index/4) % 32
			z = int(index/4)/32
			if offset == 0 and length == 0:
				status = self.STATUS_CHUNK_NOT_CREATED

			elif offset < 2 and offset != 0:
				status = self.STATUS_CHUNK_IN_HEADER

			# (don't forget!) offset and length comes in sectors of 4096 bytes
			elif (offset + length)*4096 > self.size:
				status = self.STATUS_CHUNK_OUT_OF_FILE

			else:
				status = self.STATUS_CHUNK_OK

			self.header[x,z] = (offset, length, timestamp, status)

	def parse_chunk_headers(self):
		for x in range(32):
			for z in range(32):
				offset, region_header_length, timestamp, status = self.header[x,z]

				if status == self.STATUS_CHUNK_NOT_CREATED:
					length = None
					compression = None
					chunk_status = self.STATUS_CHUNK_NOT_CREATED

				elif status == self.STATUS_CHUNK_OK:
					self.file.seek(offset*4096) # offset comes in sectors of 4096 bytes
					length = unpack(">I", self.file.read(4))
					length = length[0] # unpack always returns a tuple, even unpacking one element
					compression = unpack(">B",self.file.read(1))
					compression = compression[0]
					if length == 0: # chunk can't be zero length
						chunk_status = self.STATUS_CHUNK_ZERO_LENGTH
					elif length > region_header_length*4096:
						# the lengths stored in region header and chunk
						# header are not compatible
						chunk_status = self.STATUS_CHUNK_MISMATCHED_LENGTHS
					else:
						chunk_status = self.STATUS_CHUNK_OK

				elif status == self.STATUS_CHUNK_OUT_OF_FILE:
					if offset*4096 + 5 < self.size: # if possible read it, just in case it's useful
						self.file.seek(offset*4096) # offset comes in sectors of 4096 bytes
						length = unpack(">I", self.file.read(4))
						length = length[0] # unpack always returns a tuple, even unpacking one element
						compression = unpack(">B",self.file.read(1))
						compression = compression[0]
						chunk_status = self.STATUS_CHUNK_OUT_OF_FILE

					else:
						length = None
						compression = None
						chunk_status = self.STATUS_CHUNK_OUT_OF_FILE

				elif status == self.STATUS_CHUNK_IN_HEADER:
					length = None
					compression = None
					chunk_status = self.STATUS_CHUNK_IN_HEADER
		
				self.chunk_headers[x, z] = (length, compression, chunk_status)


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
				chunks.append({'x':x,'z':z,'length':length})
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
		if region_header_status == self.STATUS_CHUNK_NOT_CREATED:
			return None
			
		elif region_header_status == self.STATUS_CHUNK_IN_HEADER:
			raise RegionHeaderError('The chunk is in the region header')

		elif region_header_status == self.STATUS_CHUNK_OUT_OF_FILE:
			raise RegionHeaderError('The chunk is partially/completely outside the file')

		elif region_header_status == self.STATUS_CHUNK_OK:
			length, compression, chunk_header_status = self.chunk_headers[x, z]
			if chunk_header_status == self.STATUS_CHUNK_ZERO_LENGTH:
				raise ChunkHeaderError('The length of the chunk is 0')

			self.file.seek(offset*4*1024 + 5) # offset comes in sectors of 4096 bytes + length bytes + compression byte
			chunk = self.file.read(length-1)

			if (compression == 2):
				try:
					chunk = zlib.decompress(chunk)
					chunk = StringIO(chunk)
					return NBTFile(buffer=chunk) # pass uncompressed
				except Exception, e:
					raise ChunkDataError(str(e))
				
			elif (compression == 1):
				chunk = StringIO(chunk)
				try:
					return NBTFile(fileobj=chunk) # pass compressed; will be filtered through Gzip
				except Exception, e:
					raise ChunkDataError(str(e))
					
			else:
				raise ChunkDataError('Unknown chunk compression/format')
				
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
		if status in (self.STATUS_CHUNK_NOT_CREATED, self.STATUS_CHUNK_OUT_OF_FILE, self.STATUS_CHUNK_IN_HEADER):
			# don't trust bad headers, write at the end.
			# This chunk hasn't been generated yet, or the header is wrong
			# This chunk should just be appended to the end of the file
			self.file.seek(0,2) # go to the end of the file
			file_length = self.file.tell()-1 # current offset is file length
			total_sectors = file_length/4096
			sector = total_sectors+1
			pad_end = True
		elif status == self.STATUS_CHUNK_OK:
			# TODO TODO TODO Check if chunk_status says that the lengths are incompatible (status = self.STATUS_CHUNK_ZERO_LENGTH)
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
		timestamp = int(time.time())
		self.file.write(pack(">I", timestamp))


	def unlink_chunk(self, x, z):
		""" Removes a chunk from the header of the region file (write zeros in the offset of the chunk).
		Using only this method leaves the chunk data intact, fragmenting the region file (unconfirmed).
		This is an start to a better function remove_chunk"""
		
		self.file.seek(4*(x+z*32))
		self.file.write(pack(">IB", 0, 0)[1:])

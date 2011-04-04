""" Handle a single chunk of data (16x16x128 blocks) """
class Chunk(object):
	def __init__(self, x, z, length):
		self.coords = x,z
		self.length = length
	
	def __repr__(self):
		return "("+str(self.coords[0])+","+str(self.coords[1])+"): "+str(self.length)

def ByteToHex(byteStr):
	return "".join(["%02X " % ord(x) for x in byteStr]).strip()

""" Convenience class for dealing with a Block/data byte array """
class BlockArray(object):
	def __init__(self, blocksBytes, dataBytes):
		self.blocksList = [ord(b) for b in blocksBytes] # A list of bytes
		self.dataList = [ord(b) for b in dataBytes]

	# Get all data entries
	def get_all_data(self):
		bits = []
		for b in self.dataList:
			bits.append((b >> 15) & 15) # Big end of the byte
			bits.append(b & 15) # Little end of the byte
		return bits
	
	# Get a given X,Y,Z
	def get_block(self, x,y,z):
		"""
		Laid out like:
		(0,0,0), (0,1,0), (0,2,0) ... (0,127,0), (0,0,1), (0,1,1), (0,2,1) ... (0,127,1), (0,0,2) ... (0,127,15), (1,0,0), (1,1,0) ... (15,127,15)
		
		blocks = []
		for x in xrange(15):
		  for z in xrange(15):
		    for y in xrange(127):
		      blocks.append(Block(x,y,z))
		"""
		
		offset = y + z*128 + x*128*16
		return self.blocksList[offset]

	# Get a given X,Y,Z
	def get_data(self, x,y,z):
		offset = y + z*128 + x*128*16
		#print "Offset: "+str(offset)
		if (offset % 2 == 1):
			# offset is odd
			index = (offset-1)/2
			b = self.dataList[index]
			#print "Byte: %02X" % b
			return (b >>15) & 15 # Get big end of byte
		else:
			# offset is even
			index = offset/2
			b = self.dataList[index]
			#print "Byte: %02X" % b
			return b & 15
""" Handle a single chunk of data (16x16x128 blocks) """
from StringIO import StringIO
from struct import pack, unpack
import array, math

try:
	import Image
	PIL_enabled = True
except ImportError:
	PIL_enabled = False

class Chunk(object):
	def __init__(self, nbt):
		chunk_data = nbt['Level']
		self.coords = chunk_data['xPos'],chunk_data['zPos']
		self.blocks = BlockArray(chunk_data['Blocks'].value, chunk_data['Data'].value)

	def get_heightmap_image(self, buffer=False, gmin=False, gmax=False):
		if (not PIL_enabled): return false
		points = self.blocks.generate_heightmap(buffer, True)
		# Normalize the points
		hmin = min(points) if (gmin == False) else gmin # Allow setting the min/max explicitly, in case this is part of a bigger map
		hmax = max(points) if (gmax == False) else gmax
		hdelta = hmax-hmin+0.0
		pixels = ""
		for y in range(16):
			for x in range(16):
				# pix X => mc -Z
				# pix Y => mc X
				offset = (15-x)*16+y
				height = int((points[offset]-hmin)/hdelta*255)
				if (height < 0): height = 0
				if (height > 255): height = 255
				pixels += pack(">B", height)
		im = Image.fromstring('L', (16,16), pixels)
		return im

	def get_map(self):
		# Show an image of the chunk from above
		if (not PIL_enabled): return false
		pixels = ""
		block_colors = {
			0: {'h':0, 's':0, 'l':0},       # Air
			1: {'h':0, 's':0, 'l':32},      # Stone
			2: {'h':94, 's':42, 'l':32},    # Grass
			3: {'h':27, 's':51, 'l':15},    # Dirt
			4: {'h':0, 's':0, 'l':25},      # Cobblestone
			8: {'h':228, 's':50, 'l':23},   # Water
			9: {'h':228, 's':50, 'l':23},   # Water
			10: {'h':16, 's':100, 'l':48},  # Lava
			11: {'h':16, 's':100, 'l':48},  # Lava
			12: {'h':53, 's':22, 'l':58},   # Sand
			13: {'h':21, 's':18, 'l':20},   # Gravel
			17: {'h':35, 's':93, 'l':15},   # Wood
			18: {'h':114, 's':64, 'l':22},  # Leaves
			24: {'h':48, 's':31, 'l':40},   # Sandstone
			37: {'h':60, 's':100, 'l':60},  # Yellow Flower
			38: {'h':0, 's':100, 'l':50},   # Red Flower
			50: {'h':60, 's':100, 'l':50},  # Torch
			51: {'h':55, 's':100, 'l':50},  # Fire
			59: {'h':123, 's':60, 'l':50},  # Crops
			60: {'h':35, 's':93, 'l':15},   # Farmland
			78: {'h':240, 's':10, 'l':85},  # Snow
			79: {'h':240, 's':10, 'l':95},  # Ice
			81: {'h':126, 's':61, 'l':20},  # Cacti
			82: {'h':7, 's':62, 'l':23},    # Clay
			83: {'h':123, 's':70, 'l':50},  # Sugarcane
			86: {'h':24, 's':100, 'l':45},  # Pumpkin
			91: {'h':24, 's':100, 'l':45},  # Jack-o-lantern
		}
		for x in range(16):
			for z in range(15,-1,-1):
				# Find the highest block in this column
				ground_height = 127
				tints = []
				for y in range(127,-1,-1):
					block_id = self.blocks.get_block(x,y,z)
					block_data = self.blocks.get_data(x,y,z)
					if (block_id == 8 or block_id == 9):
						tints.append({'h':228, 's':50, 'l':23}) # Water
					elif (block_id == 18):
						if (block_data == 1):
							tints.append({'h':114, 's':64, 'l':22}) # Redwood Leaves
						elif (block_data == 2):
							tints.append({'h':93, 's':39, 'l':10}) # Birch Leaves
						else:
							tints.append({'h':114, 's':64, 'l':22}) # Normal Leaves
					elif (block_id == 79):
						tints.append({'h':240, 's':5, 'l':95}) # Ice
					elif (block_id == 51):
						tints.append({'h':55, 's':100, 'l':50}) # Fire
					elif (block_id != 0 or y == 0):
						# Here is ground level
						ground_height = y
						break

				color = block_colors[block_id] if (block_id in block_colors) else {'h':0, 's':0, 'l':100}
				height_shift = (ground_height-64)*0.25
				
				final_color = {'h':color['h'], 's':color['s'], 'l':color['l']+height_shift}
				if final_color['l'] > 100: final_color['l'] = 100
				if final_color['l'] < 0: final_color['l'] = 0
				
				# Apply tints from translucent blocks
				for tint in reversed(tints):
					final_color = hsl_slide(final_color, tint, 0.4)

				rgb = hsl2rgb(final_color['h'], final_color['s'], final_color['l'])

				pixels += pack("BBB", rgb[0], rgb[1], rgb[2])
		im = Image.fromstring('RGB', (16,16), pixels)
		return im

	def __repr__(self):
		return "("+str(self.coords[0])+","+str(self.coords[1])+")"

""" Convenience class for dealing with a Block/data byte array """
class BlockArray(object):
	def __init__(self, blocksBytes=None, dataBytes=None):
		if (blocksBytes != None):
			self.blocksList = [ord(b) for b in blocksBytes] # A list of bytes
		else:
			self.blocksList = [0]*32768 # Create an empty block list (32768 entries of zero (air))
		
		if (dataBytes != None):
			self.dataList = [ord(b) for b in dataBytes]
		else:
			self.dataList = [0]*32768 # Create an empty data list (32768 entries of zero)

	# Get all data entries
	def get_all_data(self):
		bits = []
		for b in self.dataList:
			bits.append((b >> 4) & 15) # Big end of the byte
			bits.append(b & 15) # Little end of the byte
		return bits

	def get_blocks_struct(self):
		cur_x = 0
		cur_y = 0
		cur_z = 0
		blocks = {}
		for block_id in self.blocksList:
			blocks[(cur_x,cur_y,cur_z)] = block_id
			cur_y += 1
			if (cur_y > 127):
				cur_y = 0
				cur_z += 1
				if (cur_z > 15):
					cur_z = 0
					cur_x += 1
		return blocks

	# Give blockList back as a byte array
	def get_blocks_byte_array(self, buffer=False):
		if buffer:
			length = len(self.blocksList)
			return StringIO(pack(">i", length)+self.get_blocks_byte_array())
		else:
			return array.array('B', self.blocksList).tostring()

	def get_data_byte_array(self, buffer=False):
		if buffer:
			length = len(self.dataList)/2
			return StringIO(pack(">i", length)+self.get_data_byte_array())
		else:
			return array.array('B', self.dataList).tostring()

	def generate_heightmap(self, buffer=False, as_array=False):
		if buffer:
			return StringIO(pack(">i", 256)+self.generate_heightmap()) # Length + Heightmap, ready for insertion into Chunk NBT
		else:
			bytes = []
			for z in range(16):
				for x in range(16):
					for y in range(127, -1, -1):
						offset = y + z*128 + x*128*16
						if (self.blocksList[offset] != 0 or y == 0):
							bytes.append(y+1)
							break
			if (as_array):
				return bytes
			else:
				return array.array('B', bytes).tostring()

	def set_blocks(self, list=None, dict=None, fill_air=False):
		if list:
			# Inputting a list like self.blocksList
			self.blocksList = list
		elif dict:
			# Inputting a dictionary like result of self.get_blocks_struct()
			list = []
			for x in range(16):
				for z in range(16):
					for y in range(128):
						coord = x,y,z
						offset = y + z*128 + x*128*16
						if (coord in dict):
							list.append(dict[coord])
						else:
							if (self.blocksList[offset] and not fill_air):
								list.append(self.blocksList[offset])
							else:
								list.append(0) # Air
			self.blocksList = list
		else:
			# None of the above...
			return False
		return True

	def set_block(self, x,y,z, id):
		offset = y + z*128 + x*128*16
		self.blocksList[offset] = id

	# Get a given X,Y,Z or a tuple of three coordinates
	def get_block(self, x,y,z, coord=False):
		"""
		Laid out like:
		(0,0,0), (0,1,0), (0,2,0) ... (0,127,0), (0,0,1), (0,1,1), (0,2,1) ... (0,127,1), (0,0,2) ... (0,127,15), (1,0,0), (1,1,0) ... (15,127,15)
		
		blocks = []
		for x in xrange(15):
		  for z in xrange(15):
		    for y in xrange(127):
		      blocks.append(Block(x,y,z))
		"""
		
		offset = y + z*128 + x*128*16 if (coord == False) else coord[1] + coord[2]*128 + coord[0]*128*16
		return self.blocksList[offset]

	# Get a given X,Y,Z or a tuple of three coordinates
	def get_data(self, x,y,z, coord=False):
		offset = y + z*128 + x*128*16 if (coord == False) else coord[1] + coord[2]*128 + coord[0]*128*16
		if (offset % 2 == 1):
			# offset is odd
			index = (offset-1)/2
			b = self.dataList[index]
			return (b >>15) & 15 # Get big end of byte
		else:
			# offset is even
			index = offset/2
			b = self.dataList[index]
			return b & 15

## Color functions for map generation ##

# Hue given in degrees,
# saturation and lightness given either in range 0-1 or 0-100 and returned in kind
def hsl_slide(hsl1, hsl2, ratio):
	if (abs(hsl2['h'] - hsl1['h']) > 180):
		if (hsl1['h'] > hsl2['h']):
			hsl1['h'] -= 360
		else:
			hsl1['h'] += 360
	
	# Find location of two colors on the H/S color circle
	p1x = math.cos(math.radians(hsl1['h']))*hsl1['s']
	p1y = math.sin(math.radians(hsl1['h']))*hsl1['s']
	p2x = math.cos(math.radians(hsl2['h']))*hsl2['s']
	p2y = math.sin(math.radians(hsl2['h']))*hsl2['s']
	
	# Slide part of the way from tint to base color
	avg_x = p1x + ratio*(p2x-p1x)
	avg_y = p1y + ratio*(p2y-p1y)
	avg_h = math.atan(avg_y/avg_x)
	avg_s = avg_y/math.sin(avg_h)
	avg_l = hsl1['l'] + ratio*(hsl2['l']-hsl1['l'])
	avg_h = math.degrees(avg_h)
	
	#print 'tint:',tint, 'base:',final_color, 'avg:',avg_h,avg_s,avg_l
	return {'h':avg_h, 's':avg_s, 'l':avg_l}


# From http://www.easyrgb.com/index.php?X=MATH&H=19#text19
def hsl2rgb(H,S,L):
	H = H/360.0
	S = S/100.0 # Turn into a percentage
	L = L/100.0
	if (S == 0):
		return (int(L*255), int(L*255), int(L*255))
	var_2 = L * (1+S) if (L < 0.5) else (L+S) - (S*L)
	var_1 = 2*L - var_2

	def hue2rgb(v1, v2, vH):
		if (vH < 0): vH += 1
		if (vH > 1): vH -= 1
		if ((6*vH)<1): return v1 + (v2-v1)*6*vH
		if ((2*vH)<1): return v2
		if ((3*vH)<2): return v1 + (v2-v1)*(2/3.0-vH)*6
		return v1
		
	R = int(255*hue2rgb(var_1, var_2, H + (1.0/3)))
	G = int(255*hue2rgb(var_1, var_2, H))
	B = int(255*hue2rgb(var_1, var_2, H - (1.0/3)))
	return (R,G,B)
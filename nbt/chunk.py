"""
Handles a single chunk of data (16x16x128 blocks) from a Minecraft save.

WARNING: Chunk is currently McRegion only.
You likely should not use chunk, but instead just get the NBT datastructure,
and do the appropriate lookups and block conversions yourself.

The authors decided to focus on NBT datastructure and Region files, 
and are not actively working on chunk.py.
Code contributions to chunk.py are welcomed!
"""
from io import BytesIO
from struct import pack, unpack
import array, math

class Chunk(object):
    """Class for representing a single chunk."""
    def __init__(self, nbt):
        chunk_data = nbt['Level']
        self.coords = chunk_data['xPos'],chunk_data['zPos']

    def get_coords(self):
        """Return the coordinates of this chunk."""
        return (self.coords[0].value,self.coords[1].value)

    def __repr__(self):
        """Return a representation of this Chunk."""
        return "Chunk("+str(self.coords[0])+","+str(self.coords[1])+")"


class McRegionChunk(Chunk):
    def __init__(self, nbt):
        Chunk.__init__(self, nbt)
        self.blocks = BlockArray(nbt['Level']['Blocks'].value, nbt['Level']['Data'].value)

# TODO: Add class AnvilChunk(Chunk)

class BlockArray(object):
    """Convenience class for dealing with a Block/data byte array."""
    def __init__(self, blocksBytes=None, dataBytes=None):
        """Create a new BlockArray, defaulting to no block or data bytes."""
        if isinstance(blocksBytes, (bytearray, array.array)):
            self.blocksList = list(blocksBytes)
        else:
            self.blocksList = [0]*32768 # Create an empty block list (32768 entries of zero (air))

        if isinstance(dataBytes, (bytearray, array.array)):
            self.dataList = list(dataBytes)
        else:
            self.dataList = [0]*16384 # Create an empty data list (32768 4-bit entries of zero make 16384 byte entries)

    # Get all block entries
    def get_all_blocks(self):
        """Return the blocks that are in this BlockArray."""
        return self.blocksList

    # Get all data entries
    def get_all_data(self):
        """Return the data of all the blocks in this BlockArray."""
        bits = []
        for b in self.dataList:
            # The first byte of the Blocks arrays correspond
            # to the LEAST significant bits of the first byte of the Data.
            # NOT to the MOST significant bits, as you might expected.
            bits.append(b & 15) # Little end of the byte
            bits.append((b >> 4) & 15) # Big end of the byte
        return bits

    # Get all block entries and data entries as tuples
    def get_all_blocks_and_data(self):
        """Return both blocks and data, packed together as tuples."""
        return list(zip(self.get_all_blocks(), self.get_all_data()))

    def get_blocks_struct(self):
        """Return a dictionary with block ids keyed to (x, y, z)."""
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
        """Return a list of all blocks in this chunk."""
        if buffer:
            length = len(self.blocksList)
            return BytesIO(pack(">i", length)+self.get_blocks_byte_array())
        else:
            return array.array('B', self.blocksList).tostring()

    def get_data_byte_array(self, buffer=False):
        """Return a list of data for all blocks in this chunk."""
        if buffer:
            length = len(self.dataList)
            return BytesIO(pack(">i", length)+self.get_data_byte_array())
        else:
            return array.array('B', self.dataList).tostring()

    def generate_heightmap(self, buffer=False, as_array=False):
        """Return a heightmap, representing the highest solid blocks in this chunk."""
        non_solids = [0, 8, 9, 10, 11, 38, 37, 32, 31]
        if buffer:
            return BytesIO(pack(">i", 256)+self.generate_heightmap()) # Length + Heightmap, ready for insertion into Chunk NBT
        else:
            bytes = []
            for z in range(16):
                for x in range(16):
                    for y in range(127, -1, -1):
                        offset = y + z*128 + x*128*16
                        if (self.blocksList[offset] not in non_solids or y == 0):
                            bytes.append(y+1)
                            break
            if (as_array):
                return bytes
            else:
                return array.array('B', bytes).tostring()

    def set_blocks(self, list=None, dict=None, fill_air=False):
        """
        Sets all blocks in this chunk, using either a list or dictionary.  
        Blocks not explicitly set can be filled to air by setting fill_air to True.
        """
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

    def set_block(self, x,y,z, id, data=0):
        """Sets the block a x, y, z to the specified id, and optionally data."""
        offset = y + z*128 + x*128*16
        self.blocksList[offset] = id
        if (offset % 2 == 1):
            # offset is odd
            index = (offset-1)//2
            b = self.dataList[index]
            self.dataList[index] = (b & 240) + (data & 15) # modify lower bits, leaving higher bits in place
        else:
            # offset is even
            index = offset//2
            b = self.dataList[index]
            self.dataList[index] = (b & 15) + (data << 4 & 240) # modify ligher bits, leaving lower bits in place

    # Get a given X,Y,Z or a tuple of three coordinates
    def get_block(self, x,y,z, coord=False):
        """Return the id of the block at x, y, z."""
        """
        Laid out like:
        (0,0,0), (0,1,0), (0,2,0) ... (0,127,0), (0,0,1), (0,1,1), (0,2,1) ... (0,127,1), (0,0,2) ... (0,127,15), (1,0,0), (1,1,0) ... (15,127,15)
        
        ::
        
          blocks = []
          for x in range(15):
            for z in range(15):
              for y in range(127):
                blocks.append(Block(x,y,z))
        """

        offset = y + z*128 + x*128*16 if (coord == False) else coord[1] + coord[2]*128 + coord[0]*128*16
        return self.blocksList[offset]

    # Get a given X,Y,Z or a tuple of three coordinates
    def get_data(self, x,y,z, coord=False):
        """Return the data of the block at x, y, z."""
        offset = y + z*128 + x*128*16 if (coord == False) else coord[1] + coord[2]*128 + coord[0]*128*16
        # The first byte of the Blocks arrays correspond
        # to the LEAST significant bits of the first byte of the Data.
        # NOT to the MOST significant bits, as you might expected.
        if (offset % 2 == 1):
            # offset is odd
            index = (offset-1)//2
            b = self.dataList[index]
            return b & 15 # Get little (last 4 bits) end of byte
        else:
            # offset is even
            index = offset//2
            b = self.dataList[index]
            return (b >> 4) & 15 # Get big end (first 4 bits) of byte

    def get_block_and_data(self, x,y,z, coord=False):
        """Return the tuple of (id, data) for the block at x, y, z"""
        return (self.get_block(x,y,z,coord),self.get_data(x,y,z,coord))


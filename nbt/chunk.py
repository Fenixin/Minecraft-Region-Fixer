"""
Handles a single chunk of data (16x16x128 blocks) from a Minecraft save.

For more information about the chunck format:
https://minecraft.gamepedia.com/Chunk_format
"""

from io import BytesIO
from struct import pack
from math import ceil
import array


# Legacy numeric block identifiers
# mapped to alpha identifiers in best effort
# See https://minecraft.gamepedia.com/Java_Edition_data_values/Pre-flattening
# TODO: move this map into a separate file

block_ids = {
      0: 'air',
      1: 'stone',
      2: 'grass_block',
      3: 'dirt',
      4: 'cobblestone',
      5: 'oak_planks',
      6: 'sapling',
      7: 'bedrock',
      8: 'flowing_water',
      9: 'water',
     10: 'flowing_lava',
     11: 'lava',
     12: 'sand',
     13: 'gravel',
     14: 'gold_ore',
     15: 'iron_ore',
     16: 'coal_ore',
     17: 'oak_log',
     18: 'oak_leaves',
     19: 'sponge',
     20: 'glass',
     21: 'lapis_ore',
     24: 'sandstone',
     30: 'cobweb',
     31: 'grass',
     32: 'dead_bush',
     35: 'white_wool',
     37: 'dandelion',
     38: 'poppy',
     39: 'brown_mushroom',
     40: 'red_mushroom',
     43: 'stone_slab',
     44: 'stone_slab',
     47: 'bookshelf',
     48: 'mossy_cobblestone',
     49: 'obsidian',
     50: 'torch',
     51: 'fire',
     52: 'spawner',
     53: 'oak_stairs',
     54: 'chest',
     56: 'diamond_ore',
     58: 'crafting_table',
     59: 'wheat',
     60: 'farmland',
     61: 'furnace',
     62: 'furnace',
     63: 'sign',  # will change to oak_sign in 1.14
     64: 'oak_door',
     65: 'ladder',
     66: 'rail',
     67: 'cobblestone_stairs',
     72: 'oak_pressure_plate',
     73: 'redstone_ore',
     74: 'redstone_ore',
     78: 'snow',
     79: 'ice',
     81: 'cactus',
     82: 'clay',
     83: 'sugar_cane',
     85: 'oak_fence',
     86: 'pumpkin',
     91: 'lit_pumpkin',
    101: 'iron_bars',
    102: 'glass_pane',
    }


def block_id_to_name(bid):
    try:
        name = block_ids[bid]
    except KeyError:
        name = 'unknown_%d' % (bid,)
        print("warning: unknown block id %i" % bid)
        print("hint: add that block to the 'block_ids' map")
    return name


# Generic Chunk

class Chunk(object):
    """Class for representing a single chunk."""
    def __init__(self, nbt):
        self.chunk_data = nbt['Level']
        self.coords = self.chunk_data['xPos'],self.chunk_data['zPos']

    def get_coords(self):
        """Return the coordinates of this chunk."""
        return (self.coords[0].value,self.coords[1].value)

    def __repr__(self):
        """Return a representation of this Chunk."""
        return "Chunk("+str(self.coords[0])+","+str(self.coords[1])+")"


# Chunk in Region old format

class McRegionChunk(Chunk):

    def __init__(self, nbt):
        Chunk.__init__(self, nbt)
        self.blocks = BlockArray(self.chunk_data['Blocks'].value, self.chunk_data['Data'].value)

    def get_max_height(self):
        return 127

    def get_block(self, x, y, z):
        name = block_id_to_name(self.blocks.get_block(x, y, z))
        return name

    def iter_block(self):
        for y in range(0, 128):
            for z in range(0, 16):
                for x in range(0, 16):
                    yield self.get_block(x, y, z)


# Section in Anvil new format

class AnvilSection(object):

    def __init__(self, nbt, version):
        self.names = []
        self.indexes = []

        # Is the section flattened ?
        # See https://minecraft.gamepedia.com/1.13/Flattening

        if version == 0 or version == 1343:  # 1343 = MC 1.12.2
            self._init_array(nbt)
        elif version >= 1631 and version <= 2230:  # MC 1.13 to MC 1.15.2
            self._init_index_unpadded(nbt)
        elif version >= 2566 and version <= 2730: # MC 1.16.0 to MC 1.17.2 (latest tested version)
            self._init_index_padded(nbt)
        else:
            raise NotImplementedError()

        # Section contains 4096 blocks whatever data version

        assert len(self.indexes) == 4096


    # Decode legacy section
    # Contains an array of block numeric identifiers

    def _init_array(self, nbt):
        bids = []
        for bid in nbt['Blocks'].value:
            try:
                i = bids.index(bid)
            except ValueError:
                bids.append(bid)
                i = len(bids) - 1
            self.indexes.append(i)

        for bid in bids:
            bname = block_id_to_name(bid)
            self.names.append(bname)


    # Decode modern section
    # Contains palette of block names and indexes packed with run-on between elements (pre 1.16 format)

    def _init_index_unpadded(self, nbt):

        for p in nbt['Palette']:
            name = p['Name'].value
            self.names.append(name)

        states = nbt['BlockStates'].value

        # Block states are packed into an array of longs
        # with variable number of bits per block (min: 4)

        num_bits = (len(self.names) - 1).bit_length()
        if num_bits < 4: num_bits = 4
        assert num_bits == len(states) * 64 / 4096
        mask = pow(2, num_bits) - 1

        i = 0
        bits_left = 64
        curr_long = states[0]

        for _ in range(0,4096):
            if bits_left == 0:
                i = i + 1
                curr_long = states[i]
                bits_left = 64

            if num_bits <= bits_left:
                self.indexes.append(curr_long & mask)
                curr_long = curr_long >> num_bits
                bits_left = bits_left - num_bits
            else:
                i = i + 1
                next_long = states[i]
                remaining_bits = num_bits - bits_left

                next_long = (next_long & (pow(2, remaining_bits) - 1)) << bits_left
                curr_long = (curr_long & (pow(2, bits_left) - 1))
                self.indexes.append(next_long | curr_long)

                curr_long = states[i]
                curr_long = curr_long >> remaining_bits
                bits_left = 64 - remaining_bits


    # Decode modern section
    # Contains palette of block names and indexes packed with padding if elements don't fit (post 1.16 format)

    def _init_index_padded(self, nbt):

        for p in nbt['Palette']:
            name = p['Name'].value
            self.names.append(name)

        states = nbt['BlockStates'].value
        num_bits = (len(self.names) - 1).bit_length()
        if num_bits < 4: num_bits = 4
        mask = 2**num_bits - 1
        
        indexes_per_element = 64 // num_bits
        last_state_elements = 4096 % indexes_per_element
        if last_state_elements == 0: last_state_elements = indexes_per_element
        
        assert len(states) == ceil(4096 / indexes_per_element)

        for i in range(len(states)-1):
            long = states[i]
            
            for _ in range(indexes_per_element):
                self.indexes.append(long & mask)
                long = long >> num_bits

        
        long = states[-1]
        for _ in range(last_state_elements):
            self.indexes.append(long & mask)
            long = long >> num_bits
        


    def get_block(self, x, y, z):
        # Blocks are stored in YZX order
        i = y * 256 + z * 16 + x
        p = self.indexes[i]
        return self.names[p]


    def iter_block(self):
        for i in range(0, 4096):
            p = self.indexes[i]
            yield self.names[p]


# Chunck in Anvil new format
 
class AnvilChunk(Chunk):

    def __init__(self, nbt):
        Chunk.__init__(self, nbt)

        # Started to work on this class with MC version 1.13.2
        # so with the chunk data version 1631
        # Backported to first Anvil version (= 0) from examples
        # Could work with other versions, but has to be tested first

        try:
            version = nbt['DataVersion'].value
            if version != 1343 and not (version >= 1631 or version <= 2730):
                raise NotImplementedError('DataVersion %d not implemented' % (version,))
        except KeyError:
            version = 0

        # Load all sections

        self.sections = {}
        if 'Sections' in self.chunk_data:
            for s in self.chunk_data['Sections']:
                if "BlockStates" in s.keys(): # sections may only contain lighting information
                    self.sections[s['Y'].value] = AnvilSection(s, version)


    def get_section(self, y):
        """Get a section from Y index."""
        if y in self.sections:
            return self.sections[y]

        return None


    def get_max_height(self):
        ymax = 0
        for y in self.sections.keys():
            if y > ymax: ymax = y
        return ymax * 16 + 15


    def get_block(self, x, y, z):
        """Get a block from relative x,y,z."""
        sy,by = divmod(y, 16)
        section = self.get_section(sy)
        if section == None:
            return None

        return section.get_block(x, by, z)


    def iter_block(self):
        for s in self.sections.values():
            for b in s.iter_block():
                yield b


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

"""
Handle a region file, containing 32x32 chunks.

For more information about the region file format:
https://minecraft.gamepedia.com/Region_file_format
"""

from .nbt import NBTFile, MalformedFileError
from struct import pack, unpack
try:
    from collections.abc import Mapping
except ImportError:  # for Python 2.7
    from collections import Mapping
import zlib
import gzip
from io import BytesIO
import time
from os import SEEK_END

# constants

SECTOR_LENGTH = 4096
"""Constant indicating the length of a sector. A Region file is divided in sectors of 4096 bytes each."""

# TODO: move status codes to an (Enum) object

# Status is a number representing:
# -5 = Error, the chunk is overlapping with another chunk
# -4 = Error, the chunk length is too large to fit in the sector length in the region header
# -3 = Error, chunk header has a 0 length
# -2 = Error, chunk inside the header of the region file
# -1 = Error, chunk partially/completely outside of file
#  0 = Ok
#  1 = Chunk non-existant yet
STATUS_CHUNK_OVERLAPPING = -5
"""Constant indicating an error status: the chunk is allocated to a sector already occupied by another chunk"""
STATUS_CHUNK_MISMATCHED_LENGTHS = -4
"""Constant indicating an error status: the region header length and the chunk length are incompatible"""
STATUS_CHUNK_ZERO_LENGTH = -3
"""Constant indicating an error status: chunk header has a 0 length"""
STATUS_CHUNK_IN_HEADER = -2
"""Constant indicating an error status: chunk inside the header of the region file"""
STATUS_CHUNK_OUT_OF_FILE = -1
"""Constant indicating an error status: chunk partially/completely outside of file"""
STATUS_CHUNK_OK = 0
"""Constant indicating an normal status: the chunk exists and the metadata is valid"""
STATUS_CHUNK_NOT_CREATED = 1
"""Constant indicating an normal status: the chunk does not exist"""

COMPRESSION_NONE = 0
"""Constant indicating that the chunk is not compressed."""
COMPRESSION_GZIP = 1
"""Constant indicating that the chunk is GZip compressed."""
COMPRESSION_ZLIB = 2
"""Constant indicating that the chunk is zlib compressed."""


# TODO: reconsider these errors. where are they catched? Where would an implementation make a difference in handling the different exceptions.

class RegionFileFormatError(Exception):
    """Base class for all file format errors.
    Note: InconceivedChunk is not a child class, because it is not considered a format error."""
    def __init__(self, msg=""):
        self.msg = msg
    def __str__(self):
        return self.msg

class NoRegionHeader(RegionFileFormatError):
    """The size of the region file is too small to contain a header."""

class RegionHeaderError(RegionFileFormatError):
    """Error in the header of the region file for a given chunk."""

class ChunkHeaderError(RegionFileFormatError):
    """Error in the header of a chunk, included the bytes of length and byte version."""

class ChunkDataError(RegionFileFormatError):
    """Error in the data of a chunk."""

class InconceivedChunk(LookupError):
    """Specified chunk has not yet been generated."""
    def __init__(self, msg=""):
        self.msg = msg


class ChunkMetadata(object):
    """
    Metadata for a particular chunk found in the 8 kiByte header and 5-byte chunk header.
    """

    def __init__(self, x, z):
        self.x = x
        """x-coordinate of the chunk in the file"""
        self.z = z
        """z-coordinate of the chunk in the file"""
        self.blockstart = 0
        """start of the chunk block, counted in 4 kiByte sectors from the
        start of the file. (24 bit int)"""
        self.blocklength = 0
        """amount of 4 kiBytes sectors in the block (8 bit int)"""
        self.timestamp = 0
        """a Unix timestamps (seconds since epoch) (32 bits), found in the
        second sector in the file."""
        self.length = 0
        """length of the block in bytes. This excludes the 4-byte length header,
        and includes the 1-byte compression byte. (32 bit int)"""
        self.compression = None
        """type of compression used for the chunk block. (8 bit int).
    
        - 0: uncompressed
        - 1: gzip compression
        - 2: zlib compression"""
        self.status = STATUS_CHUNK_NOT_CREATED
        """status as determined from blockstart, blocklength, length, file size
        and location of other chunks in the file.
        
        - STATUS_CHUNK_OVERLAPPING
        - STATUS_CHUNK_MISMATCHED_LENGTHS
        - STATUS_CHUNK_ZERO_LENGTH
        - STATUS_CHUNK_IN_HEADER
        - STATUS_CHUNK_OUT_OF_FILE
        - STATUS_CHUNK_OK
        - STATUS_CHUNK_NOT_CREATED"""
    def __str__(self):
        return "%s(%d, %d, sector=%s, blocklength=%s, timestamp=%s, bytelength=%s, compression=%s, status=%s)" % \
            (self.__class__.__name__, self.x, self.z, self.blockstart, self.blocklength, self.timestamp, \
            self.length, self.compression, self.status)
    def __repr__(self):
        return "%s(%d,%d)" % (self.__class__.__name__, self.x, self.z)
    def requiredblocks(self):
        # slightly faster variant of: floor(self.length + 4) / 4096))
        return (self.length + 3 + SECTOR_LENGTH) // SECTOR_LENGTH
    def is_created(self):
        """return True if this chunk is created according to the header.
        This includes chunks which are not readable for other reasons."""
        return self.blockstart != 0

class _HeaderWrapper(Mapping):
    """Wrapper around self.metadata to emulate the old self.header variable"""
    def __init__(self, metadata):
        self.metadata = metadata
    def __getitem__(self, xz):
        m = self.metadata[xz]
        return (m.blockstart, m.blocklength, m.timestamp, m.status)
    def __iter__(self):
        return iter(self.metadata) # iterates over the keys
    def __len__(self):
        return len(self.metadata)
class _ChunkHeaderWrapper(Mapping):
    """Wrapper around self.metadata to emulate the old self.chunk_headers variable"""
    def __init__(self, metadata):
        self.metadata = metadata
    def __getitem__(self, xz):
        m = self.metadata[xz]
        return (m.length if m.length > 0 else None, m.compression, m.status)
    def __iter__(self):
        return iter(self.metadata) # iterates over the keys
    def __len__(self):
        return len(self.metadata)

class Location(object):
    def __init__(self, x=None, y=None, z=None):
        self.x = x
        self.y = y
        self.z = z
    def __str__(self):
        return "%s(x=%s, y=%s, z=%s)" % (self.__class__.__name__, self.x, self.y, self.z)

class RegionFile(object):
    """A convenience class for extracting NBT files from the Minecraft Beta Region Format."""
    
    # Redefine constants for backward compatibility.
    STATUS_CHUNK_OVERLAPPING = STATUS_CHUNK_OVERLAPPING
    """Constant indicating an error status: the chunk is allocated to a sector
    already occupied by another chunk. 
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_OVERLAPPING` instead."""
    STATUS_CHUNK_MISMATCHED_LENGTHS = STATUS_CHUNK_MISMATCHED_LENGTHS
    """Constant indicating an error status: the region header length and the chunk
    length are incompatible. Deprecated. Use :const:`nbt.region.STATUS_CHUNK_MISMATCHED_LENGTHS` instead."""
    STATUS_CHUNK_ZERO_LENGTH = STATUS_CHUNK_ZERO_LENGTH
    """Constant indicating an error status: chunk header has a 0 length.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_ZERO_LENGTH` instead."""
    STATUS_CHUNK_IN_HEADER = STATUS_CHUNK_IN_HEADER
    """Constant indicating an error status: chunk inside the header of the region file.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_IN_HEADER` instead."""
    STATUS_CHUNK_OUT_OF_FILE = STATUS_CHUNK_OUT_OF_FILE
    """Constant indicating an error status: chunk partially/completely outside of file.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_OUT_OF_FILE` instead."""
    STATUS_CHUNK_OK = STATUS_CHUNK_OK
    """Constant indicating an normal status: the chunk exists and the metadata is valid.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_OK` instead."""
    STATUS_CHUNK_NOT_CREATED = STATUS_CHUNK_NOT_CREATED
    """Constant indicating an normal status: the chunk does not exist.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_NOT_CREATED` instead."""
    
    def __init__(self, filename=None, fileobj=None, chunkclass = None):
        """
        Read a region file by filename or file object. 
        If a fileobj is specified, it is not closed after use; it is the callers responibility to close it.
        """
        self.file = None
        self.filename = None
        self._closefile = False
        self.closed = False
        """Set to true if `close()` was successfully called on that region"""
        self.chunkclass = chunkclass
        if filename:
            self.filename = filename
            self.file = open(filename, 'r+b') # open for read and write in binary mode
            self._closefile = True
        elif fileobj:
            if hasattr(fileobj, 'name'):
                self.filename = fileobj.name
            self.file = fileobj
        elif not self.file:
            raise ValueError("RegionFile(): Need to specify either a filename or a file object")

        # Some variables
        self.metadata = {}
        """
        dict containing ChunkMetadata objects, gathered from metadata found in the
        8 kiByte header and 5-byte chunk header.
        
        ``metadata[x, z]: ChunkMetadata()``
        """
        self.header = _HeaderWrapper(self.metadata)
        """
        dict containing the metadata found in the 8 kiByte header:
        
        ``header[x, z]: (offset, sectionlength, timestamp, status)``
        
        :offset: counts in 4 kiByte sectors, starting from the start of the file. (24 bit int)
        :blocklength: is in 4 kiByte sectors (8 bit int)
        :timestamp: is a Unix timestamps (seconds since epoch) (32 bits)
        :status: can be any of:
        
            - STATUS_CHUNK_OVERLAPPING
            - STATUS_CHUNK_MISMATCHED_LENGTHS
            - STATUS_CHUNK_ZERO_LENGTH
            - STATUS_CHUNK_IN_HEADER
            - STATUS_CHUNK_OUT_OF_FILE
            - STATUS_CHUNK_OK
            - STATUS_CHUNK_NOT_CREATED
        
        Deprecated. Use :attr:`metadata` instead.
        """
        self.chunk_headers = _ChunkHeaderWrapper(self.metadata)
        """
        dict containing the metadata found in each chunk block:
        
        ``chunk_headers[x, z]: (length, compression, chunk_status)``
        
        :chunk length: in bytes, starting from the compression byte (32 bit int)
        :compression: is 1 (Gzip) or 2 (bzip) (8 bit int)
        :chunk_status: is equal to status in :attr:`header`.
        
        If the chunk is not defined, the tuple is (None, None, STATUS_CHUNK_NOT_CREATED)
        
        Deprecated. Use :attr:`metadata` instead.
        """

        self.loc = Location()
        """Optional: x,z location of a region within a world."""
        
        self._init_header()
        self._parse_header()
        self._parse_chunk_headers()

    def get_size(self):
        """ Returns the file size in bytes. """
        # seek(0,2) jumps to 0-bytes from the end of the file.
        # Python 2.6 support: seek does not yet return the position.
        self.file.seek(0, SEEK_END)
        return self.file.tell()

    @staticmethod
    def _bytes_to_sector(bsize, sectorlength=SECTOR_LENGTH):
        """Given a size in bytes, return how many sections of length sectorlen are required to contain it.
        This is equivalent to ceil(bsize/sectorlen), if Python would use floating
        points for division, and integers for ceil(), rather than the other way around."""
        sectors, remainder = divmod(bsize, sectorlength)
        return sectors if remainder == 0 else sectors + 1
    
    def close(self):
        """
        Clean up resources after use.
        
        Note that the instance is no longer readable nor writable after calling close().
        The method is automatically called by garbage collectors, but made public to
        allow explicit cleanup.
        """
        if self._closefile:
            try:
                self.file.close()
                self.closed = True
            except IOError:
                pass

    def __del__(self):
        self.close()
        # Parent object() has no __del__ method, otherwise it should be called here.

    def _init_file(self):
        """Initialise the file header. This will erase any data previously in the file."""
        header_length = 2*SECTOR_LENGTH
        if self.size > header_length:
            self.file.truncate(header_length)
        self.file.seek(0)
        self.file.write(header_length*b'\x00')
        self.size = header_length

    def _init_header(self):
        for x in range(32):
            for z in range(32):
                self.metadata[x,z] = ChunkMetadata(x, z)

    def _parse_header(self):
        """Read the region header and stores: offset, length and status."""
        # update the file size, needed when parse_header is called after
        # we have unlinked a chunk or writed a new one
        self.size = self.get_size()

        if self.size == 0:
            # Some region files seems to have 0 bytes of size, and
            # Minecraft handle them without problems. Take them
            # as empty region files.
            return
        elif self.size < 2*SECTOR_LENGTH:
            raise NoRegionHeader('The region file is %d bytes, too small in size to have a header.' % self.size)
        
        for index in range(0, SECTOR_LENGTH, 4):
            x = int(index//4) % 32
            z = int(index//4)//32
            m = self.metadata[x, z]
            
            self.file.seek(index)
            offset, length = unpack(">IB", b"\0" + self.file.read(4))
            m.blockstart, m.blocklength = offset, length
            self.file.seek(index + SECTOR_LENGTH)
            m.timestamp = unpack(">I", self.file.read(4))[0]
            
            if offset == 0 and length == 0:
                m.status = STATUS_CHUNK_NOT_CREATED
            elif length == 0:
                m.status = STATUS_CHUNK_ZERO_LENGTH
            elif offset < 2 and offset != 0:
                m.status = STATUS_CHUNK_IN_HEADER
            elif SECTOR_LENGTH * offset + 5 > self.size:
                # Chunk header can't be read.
                m.status = STATUS_CHUNK_OUT_OF_FILE
            else:
                m.status = STATUS_CHUNK_OK
        
        # Check for chunks overlapping in the file
        for chunks in self._sectors()[2:]:
            if len(chunks) > 1:
                # overlapping chunks
                for m in chunks:
                    # Update status, unless these more severe errors take precedence
                    if m.status not in (STATUS_CHUNK_ZERO_LENGTH, STATUS_CHUNK_IN_HEADER, 
                                        STATUS_CHUNK_OUT_OF_FILE):
                        m.status = STATUS_CHUNK_OVERLAPPING

    def _parse_chunk_headers(self):
        for x in range(32):
            for z in range(32):
                m = self.metadata[x, z]
                if m.status not in (STATUS_CHUNK_OK, STATUS_CHUNK_OVERLAPPING, \
                                    STATUS_CHUNK_MISMATCHED_LENGTHS):
                    # skip to next if status is NOT_CREATED, OUT_OF_FILE, IN_HEADER,
                    # ZERO_LENGTH or anything else.
                    continue
                try:
                    self.file.seek(m.blockstart*SECTOR_LENGTH) # offset comes in sectors of 4096 bytes
                    length = unpack(">I", self.file.read(4))
                    m.length = length[0] # unpack always returns a tuple, even unpacking one element
                    compression = unpack(">B",self.file.read(1))
                    m.compression = compression[0]
                except IOError:
                    m.status = STATUS_CHUNK_OUT_OF_FILE
                    continue
                if m.blockstart*SECTOR_LENGTH + m.length + 4 > self.size:
                    m.status = STATUS_CHUNK_OUT_OF_FILE
                elif m.length <= 1: # chunk can't be zero length
                    m.status = STATUS_CHUNK_ZERO_LENGTH
                elif m.length + 4 > m.blocklength * SECTOR_LENGTH:
                    # There are not enough sectors allocated for the whole block
                    m.status = STATUS_CHUNK_MISMATCHED_LENGTHS

    def _sectors(self, ignore_chunk=None):
        """
        Return a list of all sectors, each sector is a list of chunks occupying the block.
        """
        sectorsize = self._bytes_to_sector(self.size)
        sectors = [[] for s in range(sectorsize)]
        sectors[0] = True # locations
        sectors[1] = True # timestamps
        for m in self.metadata.values():
            if not m.is_created():
                continue
            if ignore_chunk == m:
                continue
            if m.blocklength and m.blockstart:
                blockend = m.blockstart + max(m.blocklength, m.requiredblocks())
                # Ensure 2 <= b < sectorsize, as well as m.blockstart <= b < blockend
                for b in range(max(m.blockstart, 2), min(blockend, sectorsize)):
                    sectors[b].append(m)
        return sectors

    def _locate_free_sectors(self, ignore_chunk=None):
        """Return a list of booleans, indicating the free sectors."""
        sectors = self._sectors(ignore_chunk=ignore_chunk)
        # Sectors are considered free, if the value is an empty list.
        return [not i for i in sectors]

    def _find_free_location(self, free_locations, required_sectors=1, preferred=None):
        """
        Given a list of booleans, find a list of <required_sectors> consecutive True values.
        If no such list is found, return length(free_locations).
        Assumes first two values are always False.
        """
        # check preferred (current) location
        if preferred and all(free_locations[preferred:preferred+required_sectors]):
            return preferred
        
        # check other locations
        # Note: the slicing may exceed the free_location boundary.
        # This implementation relies on the fact that slicing will work anyway,
        # and the any() function returns True for an empty list. This ensures
        # that blocks outside the file are considered Free as well.
        
        i = 2 # First two sectors are in use by the header
        while i < len(free_locations):
            if all(free_locations[i:i+required_sectors]):
                break
            i += 1
        return i

    def get_metadata(self):
        """
        Return a list of the metadata of each chunk that is defined in te regionfile.
        This includes chunks which may not be readable for whatever reason,
        but excludes chunks that are not yet defined.
        """
        return [m for m in self.metadata.values() if m.is_created()]

    def get_chunks(self):
        """
        Return the x,z coordinates and length of the chunks that are defined in te regionfile.
        This includes chunks which may not be readable for whatever reason.

        Warning: despite the name, this function does not actually return the chunk,
        but merely it's metadata. Use get_chunk(x,z) to get the NBTFile, and then Chunk()
        to get the actual chunk.
        
        This method is deprecated. Use :meth:`get_metadata` instead.
        """
        return self.get_chunk_coords()

    def get_chunk_coords(self):
        """
        Return the x,z coordinates and length of the chunks that are defined in te regionfile.
        This includes chunks which may not be readable for whatever reason.
        
        This method is deprecated. Use :meth:`get_metadata` instead.
        """
        chunks = []
        for x in range(32):
            for z in range(32):
                m = self.metadata[x,z]
                if m.is_created():
                    chunks.append({'x': x, 'z': z, 'length': m.blocklength})
        return chunks

    def iter_chunks(self):
        """
        Yield each readable chunk present in the region.
        Chunks that can not be read for whatever reason are silently skipped.
        Warning: this function returns a :class:`nbt.nbt.NBTFile` object, use ``Chunk(nbtfile)`` to get a
        :class:`nbt.chunk.Chunk` instance.
        """
        for m in self.get_metadata():
            try:
                yield self.get_chunk(m.x, m.z)
            except RegionFileFormatError:
                pass

    # The following method will replace 'iter_chunks'
    # but the previous is kept for the moment
    # until the users update their code

    def iter_chunks_class(self):
        """
        Yield each readable chunk present in the region.
        Chunks that can not be read for whatever reason are silently skipped.
        This function returns a :class:`nbt.chunk.Chunk` instance.
        """
        for m in self.get_metadata():
            try:
                yield self.chunkclass(self.get_chunk(m.x, m.z))
            except RegionFileFormatError:
                pass

    def __iter__(self):
        return self.iter_chunks()

    def get_timestamp(self, x, z):
        """
        Return the timestamp of when this region file was last modified.
        
        Note that this returns the timestamp as-is. A timestamp may exist, 
        while the chunk does not, or it may return a timestamp of 0 even 
        while the chunk exists.
        
        To convert to an actual date, use `datetime.fromtimestamp()`.
        """
        return self.metadata[x,z].timestamp

    def chunk_count(self):
        """Return the number of defined chunks. This includes potentially corrupt chunks."""
        return len(self.get_metadata())

    def get_blockdata(self, x, z):
        """
        Return the decompressed binary data representing a chunk.
        
        May raise a RegionFileFormatError().
        If decompression of the data succeeds, all available data is returned, 
        even if it is shorter than what is specified in the header (e.g. in case
        of a truncated while and non-compressed data).
        """
        # read metadata block
        m = self.metadata[x, z]
        if m.status == STATUS_CHUNK_NOT_CREATED:
            raise InconceivedChunk("Chunk %d,%d is not present in region" % (x,z))
        elif m.status == STATUS_CHUNK_IN_HEADER:
            raise RegionHeaderError('Chunk %d,%d is in the region header' % (x,z))
        elif m.status == STATUS_CHUNK_OUT_OF_FILE and (m.length <= 1 or m.compression == None):
            # Chunk header is outside of the file.
            raise RegionHeaderError('Chunk %d,%d is partially/completely outside the file' % (x,z))
        elif m.status == STATUS_CHUNK_ZERO_LENGTH:
            if m.blocklength == 0:
                raise RegionHeaderError('Chunk %d,%d has zero length' % (x,z))
            else:
                raise ChunkHeaderError('Chunk %d,%d has zero length' % (x,z))
        elif m.blockstart * SECTOR_LENGTH + 5 >= self.size:
            raise RegionHeaderError('Chunk %d,%d is partially/completely outside the file' % (x,z))

        # status is STATUS_CHUNK_OK, STATUS_CHUNK_MISMATCHED_LENGTHS, STATUS_CHUNK_OVERLAPPING
        # or STATUS_CHUNK_OUT_OF_FILE.
        # The chunk is always read, but in case of an error, the exception may be different 
        # based on the status.

        err = None
        try:
            # offset comes in sectors of 4096 bytes + length bytes + compression byte
            self.file.seek(m.blockstart * SECTOR_LENGTH + 5)
            # Do not read past the length of the file.
            # The length in the file includes the compression byte, hence the -1.
            length = min(m.length - 1, self.size - (m.blockstart * SECTOR_LENGTH + 5))
            chunk = self.file.read(length)
            
            if (m.compression == COMPRESSION_GZIP):
                # Python 3.1 and earlier do not yet support gzip.decompress(chunk)
                f = gzip.GzipFile(fileobj=BytesIO(chunk))
                chunk = bytes(f.read())
                f.close()
            elif (m.compression == COMPRESSION_ZLIB):
                chunk = zlib.decompress(chunk)
            elif m.compression != COMPRESSION_NONE:
                raise ChunkDataError('Unknown chunk compression/format (%s)' % m.compression)
            
            return chunk
        except RegionFileFormatError:
            raise
        except Exception as e:
            # Deliberately catch the Exception and re-raise.
            # The details in gzip/zlib/nbt are irrelevant, just that the data is garbled.
            err = '%s' % e # avoid str(e) due to Unicode issues in Python 2.
        if err:
            # don't raise during exception handling to avoid the warning 
            # "During handling of the above exception, another exception occurred".
            # Python 3.3 solution (see PEP 409 & 415): "raise ChunkDataError(str(e)) from None"
            if m.status == STATUS_CHUNK_MISMATCHED_LENGTHS:
                raise ChunkHeaderError('The length in region header and the length in the header of chunk %d,%d are incompatible' % (x,z))
            elif m.status == STATUS_CHUNK_OVERLAPPING:
                raise ChunkHeaderError('Chunk %d,%d is overlapping with another chunk' % (x,z))
            else:
                raise ChunkDataError(err)

    def get_nbt(self, x, z):
        """
        Return a NBTFile of the specified chunk.
        Raise InconceivedChunk if the chunk is not included in the file.
        """
        # TODO: cache results?
        data = self.get_blockdata(x, z) # This may raise a RegionFileFormatError.
        data = BytesIO(data)
        err = None
        try:
            nbt = NBTFile(buffer=data)
            if self.loc.x != None:
                x += self.loc.x*32
            if self.loc.z != None:
                z += self.loc.z*32
            nbt.loc = Location(x=x, z=z)
            return nbt
            # this may raise a MalformedFileError. Convert to ChunkDataError.
        except MalformedFileError as e:
            err = '%s' % e # avoid str(e) due to Unicode issues in Python 2.
        if err:
            raise ChunkDataError(err)

    def get_chunk(self, x, z):
        """
        Return a NBTFile of the specified chunk.
        Raise InconceivedChunk if the chunk is not included in the file.
        
        Note: this function may be changed later to return a Chunk() rather 
        than a NBTFile() object. To keep the old functionality, use get_nbt().
        """
        return self.get_nbt(x, z)

    def write_blockdata(self, x, z, data, compression=COMPRESSION_ZLIB):
        """
        Compress the data, write it to file, and add pointers in the header so it 
        can be found as chunk(x,z).
        """
        if compression == COMPRESSION_GZIP:
            # Python 3.1 and earlier do not yet support `data = gzip.compress(data)`.
            compressed_file = BytesIO()
            f = gzip.GzipFile(fileobj=compressed_file)
            f.write(data)
            f.close()
            compressed_file.seek(0)
            data = compressed_file.read()
            del compressed_file
        elif compression == COMPRESSION_ZLIB:
            data = zlib.compress(data) # use zlib compression, rather than Gzip
        elif compression != COMPRESSION_NONE:
            raise ValueError("Unknown compression type %d" % compression)
        length = len(data)

        # 5 extra bytes are required for the chunk block header
        nsectors = self._bytes_to_sector(length + 5)

        if nsectors >= 256:
            raise ChunkDataError("Chunk is too large (%d sectors exceeds 255 maximum)" % (nsectors))

        # Ensure file has a header
        if self.size < 2*SECTOR_LENGTH:
            self._init_file()

        # search for a place where to write the chunk:
        current = self.metadata[x, z]
        free_sectors = self._locate_free_sectors(ignore_chunk=current)
        sector = self._find_free_location(free_sectors, nsectors, preferred=current.blockstart)

        # If file is smaller than sector*SECTOR_LENGTH (it was truncated), pad it with zeroes.
        if self.size < sector*SECTOR_LENGTH:
            # jump to end of file
            self.file.seek(0, SEEK_END)
            self.file.write((sector*SECTOR_LENGTH - self.size) * b"\x00")
            assert self.file.tell() == sector*SECTOR_LENGTH

        # write out chunk to region
        self.file.seek(sector*SECTOR_LENGTH)
        self.file.write(pack(">I", length + 1)) #length field
        self.file.write(pack(">B", compression)) #compression field
        self.file.write(data) #compressed data

        # Write zeros up to the end of the chunk
        remaining_length = SECTOR_LENGTH * nsectors - length - 5
        self.file.write(remaining_length * b"\x00")

        #seek to header record and write offset and length records
        self.file.seek(4 * (x + 32*z))
        self.file.write(pack(">IB", sector, nsectors)[1:])

        #write timestamp
        self.file.seek(SECTOR_LENGTH + 4 * (x + 32*z))
        timestamp = int(time.time())
        self.file.write(pack(">I", timestamp))

        # Update free_sectors with newly written block
        # This is required for calculating file truncation and zeroing freed blocks.
        free_sectors.extend((sector + nsectors - len(free_sectors)) * [True])
        for s in range(sector, sector + nsectors):
            free_sectors[s] = False
        
        # Check if file should be truncated:
        truncate_count = list(reversed(free_sectors)).index(False)
        if truncate_count > 0:
            self.size = SECTOR_LENGTH * (len(free_sectors) - truncate_count)
            self.file.truncate(self.size)
            free_sectors = free_sectors[:-truncate_count]
        
        # Calculate freed sectors
        for s in range(current.blockstart, min(current.blockstart + current.blocklength, len(free_sectors))):
            if free_sectors[s]:
                # zero sector s
                self.file.seek(SECTOR_LENGTH*s)
                self.file.write(SECTOR_LENGTH*b'\x00')
        
        # update file size and header information
        self.size = max((sector + nsectors)*SECTOR_LENGTH, self.size)
        assert self.get_size() == self.size
        current.blockstart = sector
        current.blocklength = nsectors
        current.status = STATUS_CHUNK_OK
        current.timestamp = timestamp
        current.length = length + 1
        current.compression = COMPRESSION_ZLIB

        # self.parse_header()
        # self.parse_chunk_headers()

    def write_chunk(self, x, z, nbt_file):
        """
        Pack the NBT file as binary data, and write to file in a compressed format.
        """
        data = BytesIO()
        nbt_file.write_file(buffer=data) # render to buffer; uncompressed
        self.write_blockdata(x, z, data.getvalue())

    def unlink_chunk(self, x, z):
        """
        Remove a chunk from the header of the region file.
        Fragmentation is not a problem, chunks are written to free sectors when possible.
        """
        # This function fails for an empty file. If that is the case, just return.
        if self.size < 2*SECTOR_LENGTH:
            return

        # zero the region header for the chunk (offset length and time)
        self.file.seek(4 * (x + 32*z))
        self.file.write(pack(">IB", 0, 0)[1:])
        self.file.seek(SECTOR_LENGTH + 4 * (x + 32*z))
        self.file.write(pack(">I", 0))

        # Check if file should be truncated:
        current = self.metadata[x, z]
        free_sectors = self._locate_free_sectors(ignore_chunk=current)
        truncate_count = list(reversed(free_sectors)).index(False)
        if truncate_count > 0:
            self.size = SECTOR_LENGTH * (len(free_sectors) - truncate_count)
            self.file.truncate(self.size)
            free_sectors = free_sectors[:-truncate_count]
        
        # Calculate freed sectors
        for s in range(current.blockstart, min(current.blockstart + current.blocklength, len(free_sectors))):
            if free_sectors[s]:
                # zero sector s
                self.file.seek(SECTOR_LENGTH*s)
                self.file.write(SECTOR_LENGTH*b'\x00')

        # update the header
        self.metadata[x, z] = ChunkMetadata(x, z)

    def _classname(self):
        """Return the fully qualified class name."""
        if self.__class__.__module__ in (None,):
            return self.__class__.__name__
        else:
            return "%s.%s" % (self.__class__.__module__, self.__class__.__name__)

    def __str__(self):
        if self.filename:
            return "<%s(%r)>" % (self._classname(), self.filename)
        else:
            return '<%s object at %d>' % (self._classname(), id(self))
    
    def __repr__(self):
        if self.filename:
            return "%s(%r)" % (self._classname(), self.filename)
        else:
            return '<%s object at %d>' % (self._classname(), id(self))

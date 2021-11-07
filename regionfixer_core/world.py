#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2020  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from glob import glob
from os.path import join, split, exists, isfile
from os import remove
from shutil import copy
import zlib

import nbt.region as region
import nbt.nbt as nbt
from .util import table
from nbt.nbt import TAG_List

import regionfixer_core.constants as c



class InvalidFileName(IOError):
    """ Exception raised when a filename is wrong. """
    pass


class ScannedDataFile:
    """ Stores all the information of a scanned data file. 
    
    Inputs:
     - path -- String with the path of the data file. Defaults to None.
    """

    def __init__(self, path=None):
        super().__init__()
        self.path = path
        if self.path and exists(self.path):
            self.filename = split(path)[1]
            self.folder = split(split(path)[0])[1]
        else:
            self.filename = None
        # The status of the region file.
        self.status = None

    def __str__(self):
        text = "NBT file:" + str(self.filename) + "\n"
        text += "\tStatus:" + c.DATAFILE_STATUS_TEXT[self.status] + "\n"
        return text

    @property
    def oneliner_status(self):
        """ One line describing the status of the file. """
        return "File: \"" + self.filename + "\"; status: " + c.DATAFILE_STATUS_TEXT[self.status]


class ScannedChunk:
    """ Stores all the information of a scanned chunk.
    
    Not used at the moment, it's nice but takes an huge amount of memory when
    is not strange for chunks to be in the order of millions."""
    # WARNING: This is here so I remember to not use objects as ScannedChunk
    # They take too much memory.


class ScannedRegionFile:
    """ Stores all the scan information for a region file.

    Keywords arguments:
     - path -- A string with the path of the region file
     - scanned_time -- Float, time as returned by bult-in time module. The time
               at which the region file has been scanned. None by default.
     - folder -- Used to enhance print()

    """

    def __init__(self, path, scanned_time=None, folder=""):
        # general region file info
        self.path = path
        self.filename = split(path)[1]
        self.folder = folder
        self.x = self.z = None
        self.x, self.z = self.get_coords()
        self.coords = (self.x, self.z)

        # dictionary storing all the state tuples of all the chunks
        # in the region file, keys are the local coords of the chunk
        # sometimes called header coords
        self._chunks = {}

        # Dictionary containing counters to for all the chunks
        self._counts = {}
        for s in c.CHUNK_STATUSES:
            self._counts[s] = 0

        # time when the scan for this file finished
        self.scan_time = scanned_time

        # The status of the region file.
        self.status = None

        # has the file been scanned yet?
        self.scanned = False

    @property
    def oneliner_status(self):
        """ On line description of the status of the region file. """
        if self.scanned:
            status = self.status
            if status == c.REGION_OK:  # summary with all found in scan
                stats = ""
                for s in c.CHUNK_PROBLEMS:
                    stats += "{0}:{1}, ".format(c.CHUNK_PROBLEMS_ABBR[s], self.count_chunks(s))
                stats += "t:{0}".format(self.count_chunks())
            else:
                stats = c.REGION_STATUS_TEXT[status]
        else:
            stats = "Not scanned"

        return stats

    def __str__(self):
        text = "Path: {0}".format(self.path)
        scanned = False
        if self.scan_time:
            scanned = True
        text += "\nScanned: {0}".format(scanned)

        return text

    def __getitem__(self, key):
        return self._chunks[key]

    def __setitem__(self, key, value):
        self._chunks[key] = value
        self._counts[value[c.TUPLE_STATUS]] += 1

    def get_coords(self):
        """ Returns the region file coordinates as two integers.
        
        Return:
         - coordX, coordZ -- Integers with the x and z coordinates of the 
                             region file.
        
        Either parse the region file name or uses the stored in the object.

        """

        if self.x != None and self.z != None:
            return self.x, self.z
        else:
            splited = split(self.filename)
            filename = splited[1]
            l = filename.split('.')
            try:
                coordX = int(l[1])
                coordZ = int(l[2])
            except ValueError:
                raise InvalidFileName()

            return coordX, coordZ

    def keys(self):
        """Returns a list with all the local coordinates (header coordinates).
        
        Return:
         - list -- A list with all the local chunk coordinates extracted form the 
                    region file header as integer tuples
        """

        return list(self._chunks.keys())

    @property
    def has_problems(self):
        """ Return True if the region file has problem in itself or in its chunks.
        
        Return:
         - boolean -- True f the region has problems or False otherwise.

        """

        if self.status in c.REGION_PROBLEMS:
            return True
        for s in c.CHUNK_PROBLEMS:
            if self.count_chunks(s):
                return True
        return False

    def get_path(self):
        """ Returns the path of the region file.
        
        Return:
         - path -- A string with the path of the region file.

        """

        return self.path

    def count_chunks(self, status=None):
        """ Counts chunks in the region file with the given problem.
        
        Inputs:
         - status -- Integer with the status of the chunk to count for. See
                     CHUNK_PROBLEMS in constants.py.

        Return:
         - counter -- Integer with the number of chunks with that status

        If problem is omitted or None, counts all the chunks. Returns
        an integer with the counter.

        """

        if status == None:
            counter = 0
            for s in c.CHUNK_STATUSES:
                counter += self._counts[s]
        else:
            counter = self._counts[status]

        return counter

    def get_global_chunk_coords(self, chunkX, chunkZ):
        """ Takes the chunk local coordinates and returns its global coordinates.
        
        Inputs:
         - chunkX -- Integer, local X chunk coordinate.
         - chunkZ -- Integer, local Z chunk coordinate.

        Return:
         - chunkX, chunkZ -- Integers with the x and z global chunk coordinates

        """

        regionX, regionZ = self.get_coords() 
        chunkX += regionX * 32
        chunkZ += regionZ * 32

        return chunkX, chunkZ

    def list_chunks(self, status=None):
        """ Returns a list of tuples of chunks for all the chunks with 'status'.
        
        Inputs:
         - status -- Defaults to None. Integer with the status of the chunk to list,
                     see CHUNK_STATUSES in constants.py
        
        Return:
         - list - List with tuples like (global_coordinates, status_tuple) where status 
                 tuple is (number_of_entities, status)
        
        If status is omitted or None, returns all the chunks in the region file

        """

        l = []
        for ck in list(self.keys()):
            t = self[ck]
            if status == t[c.TUPLE_STATUS]:
                l.append((self.get_global_chunk_coords(*ck), t))
            elif status == None:
                l.append((self.get_global_chunk_coords(*ck), t))

        return l

    def summary(self):
        """ Returns a summary of all the problematic chunks.
        
        Return:
         - text -- Human readable string with the summary of the scan.
        
        The summary is a human readable string with region file, global
        coordinates, local coordinates, and status of every problematic
        chunk, in a subtree like format.

        """

        text = ""
        if self.status in c.REGION_PROBLEMS:
            text += " |- This region has status: {0}.\n".format(c.REGION_STATUS_TEXT[self.status])
        else:
            for ck in list(self.keys()):
                if self[ck][c.TUPLE_STATUS] not in c.CHUNK_PROBLEMS:
                    continue
                status = self[ck][c.TUPLE_STATUS]
                h_coords = ck
                g_coords = self.get_global_chunk_coords(*h_coords)
                text += " |-+-Chunk coords: header {0}, global {1}.\n".format(h_coords, g_coords)
                text += " | +-Status: {0}\n".format(c.CHUNK_STATUS_TEXT[status])
                if self[ck][c.TUPLE_STATUS] == c.CHUNK_TOO_MANY_ENTITIES:
                    text += " | +-No. entities: {0}\n".format(self[ck][c.TUPLE_NUM_ENTITIES])
                text += " |\n"

        return text

    def remove_problematic_chunks(self, status):
        """ Removes all the chunks with the given status
        
        Inputs:
         - status -- Integer with the status of the chunks to remove.
                     See CHUNK_STATUSES in constants.py
        
        Return:
         - counter -- An integer with the amount of removed chunks.

        """

        counter = 0
        bad_chunks = self.list_chunks(status)
        for ck in bad_chunks:
            global_coords = ck[0]
            local_coords = _get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            region_file.unlink_chunk(*local_coords)
            counter += 1
            # create the new status tuple
            #                    (num_entities, chunk status)
            self[local_coords] = (0, c.CHUNK_NOT_CREATED)

        return counter

    def fix_problematic_chunks(self, status):
        """ This fixes problems in chunks that can be somehow fixed.
        
        Inputs:
         - status -- Integer with the status of the chunks to fix. See 
                    FIXABLE_CHUNK_PROBLEMS in constants.py
        
        Return:
         - counter -- An integer with the amount of fixed chunks.
        
        Right now it only fixes chunks missing the TAG_List Entities, wrong located chunks and
        in some cases corrupted chunks.
        
        -TAG_List is fixed by adding said tag.
        
        -Wrong located chunks are relocated to the data coordinates stored in the zip stream. 
         We suppose these coordinates are right because the data has checksum.
         
        -Corrupted chunks: tries to read the the compressed stream byte by byte until it raises
         exception. After that compares the size of the compressed chunk stored in the region file
         with the compressed chunk extracted from the strem, if they are the same it's good to go!

        """

        # TODO: it seems having the Entities TAG missing is just a little part. Some of the
        # chunks have like 3 or 4 tag missing from the NBT structure. I don't really know which
        # of them are mandatory.
        
        assert(status in c.FIXABLE_CHUNK_PROBLEMS)
        counter = 0
        bad_chunks = self.list_chunks(status)
        for ck in bad_chunks:
            global_coords = ck[0]
            local_coords = _get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            # catch the exception of corrupted chunks 
            try:
                chunk = region_file.get_chunk(*local_coords)
            except region.ChunkDataError:
                # if we are here the chunk is corrupted, but still
                if status == c.CHUNK_CORRUPTED:
                    # read the data raw
                    m = region_file.metadata[local_coords[0], local_coords[1]]
                    region_file.file.seek(m.blockstart * region.SECTOR_LENGTH + 5)
                    # these status doesn't provide a good enough data, we could end up reading garbage
                    if m.status not in (region.STATUS_CHUNK_IN_HEADER, region.STATUS_CHUNK_MISMATCHED_LENGTHS, 
                                       region.STATUS_CHUNK_OUT_OF_FILE, region.STATUS_CHUNK_OVERLAPPING,
                                       region.STATUS_CHUNK_ZERO_LENGTH):
                        # get the raw data of the chunk
                        raw_chunk = region_file.file.read(m.length - 1)
                        # decompress byte by byte so we can get as much as we can before the error happens
                        dc = zlib.decompressobj()
                        out = ""
                        for i in raw_chunk:
                            out += dc.decompress(i)
                        # compare the sizes of the new compressed strem and the old one to see if we've got something good
                        cdata = zlib.compress(out.encode())
                        if len(cdata) == len(raw_chunk):
                            # the chunk is probably good, write it in the region file
                            region_file.write_blockdata(local_coords[0], local_coords[1], out)
                            print("The chunk {0},{1} in region file {2} was fixed successfully.".format(local_coords[0], local_coords[1], join(self.folder,self.filename)))
                        else:
                            print("The chunk {0},{1} in region file {2} couldn't be fixed.".format(local_coords[0], local_coords[1], join(self.folder,self.filename)))
                        #=======================================================
                        # print("Extracted: " + str(len(out)))
                        # print("Size of the compressed stream: " + str(len(raw_chunk)))
                        #=======================================================
            except (region.ChunkHeaderError, region.RegionHeaderError, UnicodeDecodeError):
                # usually a chunk with zero length in the first two cases, or veeery broken chunk in the third
                print("The chunk {0},{1} in region file {2} couldn't be fixed.".format(local_coords[0], local_coords[1], join(self.folder,self.filename)))

            if status == c.CHUNK_MISSING_ENTITIES_TAG:
                # The arguments to create the empty TAG_List have been somehow extracted by comparing
                # the tag list from a healthy chunk with the one created by nbt
                chunk['Level']['Entities'] = TAG_List(name='Entities', type=nbt._TAG_End)
                region_file.write_chunk(local_coords[0],local_coords[1], chunk)

                # create the new status tuple
                #                    (num_entities, chunk status)
                self[local_coords] = (0           , c.CHUNK_NOT_CREATED)
                counter += 1

            elif status == c.CHUNK_WRONG_LOCATED:
                data_coords = get_chunk_data_coords(chunk)
                data_l_coords = _get_local_chunk_coords(*data_coords)
                region_file.write_chunk(data_l_coords[0], data_l_coords[1], chunk)
                region_file.unlink_chunk(*local_coords)
                # what to do with the old chunk in the wrong position?
                # remove it or keep it? It's probably the best to remove it.
                # create the new status tuple
                
                # remove the wrong position of the chunk and update the status 
                #                    (num_entities, chunk status)
                self[local_coords] = (0           , c.CHUNK_NOT_CREATED)
                self[data_l_coords]= (0           , c.CHUNK_OK)
                counter += 1

        return counter

    def remove_entities(self):
        """ Removes all the entities in chunks with status c.CHUNK_TOO_MANY_ENTITIES.
        
        Return:
         - counter -- Integer with the number of removed entities.

        """

        status = c.CHUNK_TOO_MANY_ENTITIES
        counter = 0
        bad_chunks = self.list_chunks(status)
        for ck in bad_chunks:
            global_coords = ck[0]
            local_coords = _get_local_chunk_coords(*global_coords)
            counter += self.remove_chunk_entities(*local_coords)
            # create new status tuple:
            #                    (num_entities, chunk status)
            self[local_coords] = (0, c.CHUNK_OK)
        return counter

    def remove_chunk_entities(self, x, z):
        """ Takes a chunk local coordinates and remove its entities.
        
        Inputs:
         - x -- Integer with the X local (header) coordinate of the chunk
         - z -- Integer with the Z local (header) coordinate of the chunk
        
        Return:
         - counter -- An integer with the number of entities removed. 
        
        This will remove all the entities in the chunk, it will not perform any
        kind of check.

        """

        region_file = region.RegionFile(self.path)
        chunk = region_file.get_chunk(x, z)
        counter = len(chunk['Level']['Entities'])
        empty_tag_list = nbt.TAG_List(nbt.TAG_Byte, '', 'Entities')
        chunk['Level']['Entities'] = empty_tag_list
        region_file.write_chunk(x, z, chunk)

        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks after changing entity_limit.
        
        Inputs:
         - options -- argparse arguments, the whole argparse.ArgumentParser() object as used
                      by regionfixer.py

        """

        for ck in list(self.keys()):
            # for safety reasons use a temporary list to generate the
            # new tuple
            t = [0, 0]
            if self[ck][c.TUPLE_STATUS] in (c.CHUNK_TOO_MANY_ENTITIES, c.CHUNK_OK):
                # only touch the ok chunks and the too many entities chunk
                if self[ck][c.TUPLE_NUM_ENTITIES] > options.entity_limit:
                    # now it's a too many entities problem
                    t[c.TUPLE_NUM_ENTITIES] = self[ck][c.TUPLE_NUM_ENTITIES]
                    t[c.TUPLE_STATUS] = c.CHUNK_TOO_MANY_ENTITIES

                elif self[c][c.TUPLE_NUM_ENTITIES] <= options.entity_limit:
                    # the new limit says it's a normal chunk
                    t[c.TUPLE_NUM_ENTITIES] = self[ck][c.TUPLE_NUM_ENTITIES]
                    t[c.TUPLE_STATUS] = c.CHUNK_OK

                self[ck] = tuple(t)


class DataSet:
    """ Stores data items to be scanned by AsyncScanner in scan.py.

    Inputs:
     - typevalue -- The type of the class to store in the set. In initialization it will be
                    asserted if it is of that type

    The data will be stored  in the self._set dictionary.
    
    Implemented private methods are: __getitem__, __setitem__, _get_list, __len__.

    Three methods should be overridden to work with a DataSet, two of the mandatory:
     - _replace_in_data_structure -- (mandatory) Should be created because during the scan the
            different processes create copies of the original data, so replacing it in
            the original data set is mandatory in order to keep everything working.

     - _update_counts -- (mandatory) Makes sure that the DataSet stores all the counts and
            that it is not needed to loop through all of them to know the real count.

     - has_problems -- (optional but used) Should return True only if any element
                         of the set has problems

    """

    def __init__(self, typevalue, *args, **kwargs):
        self._set = {}
        self._typevalue = typevalue

    def _get_list(self):
        """ Returns a list with all the values in the set. """

        return list(self._set.values())

    def __getitem__(self, key):
        return self._set[key]

    def __delitem__(self, key):
        del self._set[key]

    def __setitem__(self, key, value):
        assert self._typevalue == type(value)
        self._set[key] = value
        self._update_counts(value)

    def __len__(self):
        return len(self._set)

    # mandatory implementation methods
    def summary(self):
        """ Return a summary of problems found in this set. """

        raise NotImplementedError

    @property
    def has_problems(self):
        """ Returns True if the scanned set has problems. """

        raise NotImplementedError

    def _replace_in_data_structure(self, data, key):
        """ For multiprocessing. Replaces the data in the set with the new data.

        Inputs:
         - data -- Value of the data to be stored
         - key -- Key in which to store the data

        Child scanning processes make copies of the ScannedRegion/DataFile when they scan them.
        The AsyncScanner will call this function so the ScannedRegion/DataFile is stored
        in the set properly.
        """

        raise NotImplementedError

    def _update_counts(self, s):
        """ This functions is used by __set__ to update the counters. """

        raise NotImplementedError


class DataFileSet(DataSet):
    """ DataSet for Minecraft data files (.dat).
    
    Inputs:
     - path -- Path to the folder containing data files
     - title -- Some user readable string to represent the DataSet
    """

    def __init__(self, path, title, *args, **kwargs):
        DataSet.__init__(self, ScannedDataFile, *args, **kwargs)
        d = self._set

        self.title = title
        self.path = path
        data_files_path = glob(join(path, "*.dat"))

        for path in data_files_path:
            d[path] = ScannedDataFile(path)

        # stores the counts of files
        self._counts = {}
        for s in c.DATAFILE_STATUSES:
            self._counts[s] = 0

    @property
    def has_problems(self):
        """ Returns True if the dataset has problems and false otherwise. """

        for d in self._set.values():
            if d.status in c.DATAFILE_PROBLEMS:
                return True
        return False

    def _replace_in_data_structure(self, data):
        self._set[data.path] = data

    def _update_counts(self, s):
        assert isinstance(s, self._typevalue)
        self._counts[s.status] += 1

    def count_datafiles(self, status):
        pass

    def summary(self):
        """ Return a summary of problems found in this set. """

        text = ""
        bad_data_files = [i for i in list(self._set.values()) if i.status in c.DATAFILE_PROBLEMS]
        for f in bad_data_files:
            text += "\t" + f.oneliner_status
            text += "\n"
        return text


class RegionSet(DataSet):
    """Stores an arbitrary number of region files and their scan results.
    
    Inputs:
     - regionset_path -- Path to the folder containing region files
                         IT MUST NOT END WITH A SLASH ("/")
     - region_list -- List of paths to all the region files
     - overworld -- Tweak to tell it's a dimension and not the overworld
    """

    def __init__(self, regionset_path=None, region_list=[], overworld=True):
        DataSet.__init__(self, ScannedRegionFile)
        # Otherwise, problems in _get_dimension_directory() and _get_region_type_directory()
        if regionset_path != None :
            assert regionset_path[-1] != "/"
        self.overworld = overworld

        if regionset_path:
            self.path = regionset_path
            self.region_list = glob(join(self.path, "r.*.*.mca"))
        else:
            self.path = None
            self.region_list = region_list
        self._set = {}
        for path in self.region_list:
            try:
                r = ScannedRegionFile(path, folder=self._get_dim_type_string())
                self._set[r.get_coords()] = r

            except InvalidFileName:
                try :
                    region_type = c.REGION_TYPES_NAMES[self._get_region_type_directory()][0]
                except:
                    region_type = "region (?)"
                print("Warning: The file {0} is not a valid name for a {1} file. I'll skip it.".format(path, region_type))

        # region and chunk counters with all the data from the scan
        self._region_counters = {}
        for status in c.REGION_STATUSES:
            self._region_counters[status] = 0

        self._chunk_counters = {}
        for status in c.CHUNK_STATUSES:
            self._chunk_counters[status] = 0

        # has this regionset been scanned?
        self.scanned = False

    def get_name(self):
        """ Return a string with a representative name for the regionset

        The order for getting the name is:
         1 - The name derived by the dimension path
         2 - The name of the last directory in the path as returned by _get_dimension_directory
         3 - Empty string ""

        """

        dim_directory = self._get_dimension_directory()
        region_type_directory = self._get_region_type_directory()
        if (dim_directory or self.overworld) and region_type_directory:
            try: dim_directory = c.DIMENSION_NAMES[dim_directory]
            except: dim_directory = "\"" + dim_directory + "\""
            try: region_type_directory = c.REGION_TYPES_NAMES[region_type_directory][1]
            except: region_type_directory = "\"" + region_type_directory + "\""
            return "{0} files for {1}".format(region_type_directory, dim_directory)
        else:
            return ""

    def _get_dimension_directory(self):
        """ Returns a string with the parent directory containing the RegionSet.
        
        If there is no such a directory returns None. If it's composed
        of sparse region files returns 'regionset'.
    
        """

        if self.path:
            if self.overworld :
                return ""
            rest, type_dir = split(self.path)
            rest, dim_path = split(rest)
            return dim_path
        else:
            return None

    def _get_region_type_directory(self):
        """ Returns a string with the directory containing the RegionSet.
        
        If there is no such a directory returns None. If it's composed
        of sparse region files returns 'regionset'.
        """

        if self.path:
            rest, type_dir = split(self.path)
            return type_dir
        else:
            return None

    def _get_dim_type_string(self) :
        dim = self._get_dimension_directory()
        rg_type = self._get_region_type_directory()
        string = ""
        if rg_type != None : string = rg_type
        if dim != None and dim != "" : string = dim + "/" + rg_type
        return string

    def _update_counts(self, scanned_regionfile):
        """ Updates the counters of the regionset with the new regionfile. """

        assert isinstance(scanned_regionfile, ScannedRegionFile)

        self._region_counters[scanned_regionfile.status] += 1

        for status in c.CHUNK_STATUSES:
            self._chunk_counters[status] += scanned_regionfile.count_chunks(status)

    def _replace_in_data_structure(self, data):
        self._set[data.get_coords()] = data

    def __str__(self):
        text = "RegionSet: {0}\n".format(self.get_name())
        if self.path:
            text += "   Regionset path: {0}\n".format(self.path)
        text += "   Region files: {0}\n".format(len(self._set))
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    @property
    def has_problems(self):
        """ Returns True if the regionset has chunk or region problems and false otherwise. """

        for s in c.REGION_PROBLEMS:
            if self.count_regions(s):
                return True

        for s in c.CHUNK_PROBLEMS:
            if self.count_chunks(s):
                return True

        return False

    def keys(self):
        return list(self._set.keys())

    def list_regions(self, status=None):
        """ Returns a list of all the ScannedRegionFile objects with 'status'.
        
        Inputs:
         - status -- The region file status. See c.REGION_STATUSES
        
        Return:
         - t -- List with all the ScannedRegionFile objects with that status
        
        If status = None it returns all the objects.
        
        """

        if status is None:
            return list(self._set.values())
        t = []
        for coords in list(self._set.keys()):
            r = self._set[coords]
            if r.status == status:
                t.append(r)
        return t

    def count_regions(self, status=None):
        """ Return the number of region files with status.
        
        Inputs:
         - status -- The region file status. See c.REGION_STATUSES
        
        Return:
         - counter -- Integer with the number of regions with that status
        
        If none returns the total number of region files in this regionset.
        
        """

        counter = 0
        if status is None:
            for s in c.REGION_STATUSES:
                counter += self._region_counters[s]
        else:
            counter = self._region_counters[status]

        return counter

    def count_chunks(self, status=None):
        """ Returns the number of chunks with the given status.
        
        Inputs:
         - status -- Integer with the chunk status to count. See 
                     c.CHUNK_STATUSES in constants.py
        
        Return:
         - counter -- Integer with the number of chunks removed

        If status is None returns the number of chunks in this region file.

        """

        counter = 0
        if status is None:
            for s in c.CHUNK_STATUSES:
                counter += self._chunk_counters[s]
        else:
            counter = self._chunk_counters[status]

        return counter

    def list_chunks(self, status=None):
        """ Returns a list of all the chunk tuples with 'status'.
        
        Inputs:
         - status -- The chunk status to list. See c.CHUNK_STATUSES
        
        Return:
         - l -- List with tuples like (global_coordinates, status_tuple) where status 
                 tuple is (number_of_entities, status). For more details see
                 ScannedRegionFile.list_chunks()
        
        If status = None it returns all the chunk tuples.
        
        """

        l = []
        for r in list(self.keys()):
            l.extend(self[r].list_chunks(status))
        return l

    def summary(self):
        """ Returns a string with a summary of the problematic chunks.

        Return:
         - text -- String, human readable text with information about the scan.

        The summary contains global coordinates, local coordinates,
        data coordinates and status.

        """

        text = ""
        for r in list(self.keys()):
            if not self[r].has_problems:
                continue
            text += "Region file: {0}\n".format(join(self._get_dim_type_string(),self[r].filename))

            text += self[r].summary()
            text += " +\n\n"
        return text

    def locate_chunk(self, global_coords):
        """ Takes the global coordinates of a chunk and returns where is it.
        
        Inputs:
         - global_coords -- Tuple of two integers with the global chunk coordinates to locate.
        
        Return:
         - path -- String, with the path of the region file where
                       the chunk is stored
         - local_coords -- Tuple of two integers with local coordinates of the
                           chunk in the region file

        """

        path = join(self.path, get_chunk_region(*global_coords))
        local_coords = _get_local_chunk_coords(*global_coords)

        return path, local_coords

    def locate_region(self, coords):
        """ Returns a string with the path of the region file.
        
        Inputs:
         - coords -- Tuple of two integers with the global region coordinates of the region
                     file to locate in this RegionSet.
        
        Return:
         - region_name -- String containing the path of the region file or None if it
                          doesn't exist

        """

        x, z = coords
        region_name = 'r.' + str(x) + '.' + str(z) + '.mca'

        return region_name

    def remove_problematic_chunks(self, status):
        """ Removes all the chunks with the given status.
        
        Inputs:
         - status -- Integer with the chunk status to remove. See c.CHUNK_STATUSES
                     in constants.py for a list of possible statuses.
        
        Return:
         - counter -- Integer with the number of chunks removed
        """

        counter = 0
        if self.count_chunks():
            dim_name = self.get_name()
            print(' Deleting chunks in regionset \"{0}\":'.format(dim_name if dim_name else "selected region files"))
            for r in list(self._set.keys()):
                counter += self._set[r].remove_problematic_chunks(status)
            print("Removed {0} chunks in this regionset.\n".format(counter))

        return counter

    def fix_problematic_chunks(self, status):
        """ Try to fix all the chunks with the given problem.

        Inputs:
         - status -- Integer with the chunk status to fix. See c.CHUNK_STATUSES in constants.py
                     for a list of possible statuses.
        
        Return:
         - counter -- Integer with the number of chunks fixed.
        """

        counter = 0
        if self.count_chunks():
            dim_name = self.get_name()
            print('Repairing chunks in regionset \"{0}\":'.format(dim_name if dim_name else "selected region files"))
            for r in list(self._set.keys()):
                counter += self._set[r].fix_problematic_chunks(status)
            print("    Repaired {0} chunks in this regionset.\n".format(counter))

        return counter

    def remove_entities(self):
        """ Removes entities in chunks with the status TOO_MANY_ENTITIES. 

        Return:
         - counter -- Integer with the number of removed entities.
        """

        counter = 0
        for r in list(self._set.keys()):
            counter += self._set[r].remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the c.CHUNK_TOO_MANY_ENTITIES status of all the chunks in the RegionSet.
        
        This should be ran when the option entity limit is changed.
        """

        for r in list(self.keys()):
            self[r].rescan_entities(options)

    def generate_report(self, standalone):
        """ Generates a report with the results of the scan.
        
        Inputs:
         - standalone -- If true the report will be a human readable String. If false the 
                         report will be a dictionary with all the counts of chunks and regions.
        
        Return if standalone = True:
         - text -- A human readable string of text with the results of the scan.
         
        Return if standlone = False:
         - chunk_counts -- Dictionary with all the counts of chunks for all the statuses. To read
                           it use the CHUNK_* constants. 
         - region_counts -- Dictionary with all the counts of region files for all the statuses. To read
                            it use the REGION_* constants.

        """

        # collect chunk data
        chunk_counts = {}
        has_chunk_problems = False
        for p in c.CHUNK_PROBLEMS:
            chunk_counts[p] = self.count_chunks(p)
            if chunk_counts[p] != 0:
                has_chunk_problems = True
        chunk_counts['TOTAL'] = self.count_chunks()

        # collect region data
        region_counts = {}
        has_region_problems = False
        for p in c.REGION_PROBLEMS:
            region_counts[p] = self.count_regions(p)
            if region_counts[p] != 0:
                has_region_problems = True
        region_counts['TOTAL'] = self.count_regions()

        # create a text string with a report of all found
        if standalone:
            text = ""

            # add all chunk info in a table format
            text += "\nChunk problems:\n"
            if has_chunk_problems:
                table_data = []
                table_data.append(['Problem', 'Count'])
                for p in c.CHUNK_PROBLEMS:
                    if chunk_counts[p] != 0:
                        table_data.append([c.CHUNK_STATUS_TEXT[p], chunk_counts[p]])
                table_data.append(['Total', chunk_counts['TOTAL']])
                text += table(table_data)
            else:
                text += "No problems found.\n"

            # add all region information
            text += "\n\nRegion problems:\n"
            if has_region_problems:
                table_data = []
                table_data.append(['Problem', 'Count'])
                for p in c.REGION_PROBLEMS:
                    if region_counts[p] != 0:
                        table_data.append([c.REGION_STATUS_TEXT[p], region_counts[p]])
                table_data.append(['Total', region_counts['TOTAL']])
                text += table(table_data)

            else:
                text += "No problems found."

            return text
        else:
            return chunk_counts, region_counts

    def remove_problematic_regions(self, status):
        """ Removes all the regions files with the given status. See the warning!
        
        Inputs:
         - status -- Integer with the status of the region files to remove.
                     See c.REGION_STATUSES in constants.py for a list.
        
        Return:
         - counter -- An integer with the amount of removed region files.
        
        Warning! This is NOT the same as removing chunks, this WILL DELETE the region files 
        from the hard drive.
        """

        counter = 0
        for r in self.list_regions(status):
            remove(r.get_path())
            counter += 1
        return counter

class World:
    """ This class stores information and scan results for a Minecraft world.
    
    Inputs:
     - world_path -- String with the path of the world.
    
    Once scanned, stores all the problems found in it. It also has all the tools
    needed to modify the world.

    """

    def __init__(self, world_path):
        self.path = world_path

        # list with RegionSets
        self.regionsets = []

        self.regionsets.append(RegionSet(join(self.path, "region")))
        for directory in glob(join(self.path, "DIM*/region")):
            self.regionsets.append(RegionSet(directory, overworld=False))

        self.regionsets.append(RegionSet(join(self.path, "poi")))
        for directory in glob(join(self.path, "DIM*/poi")):
            self.regionsets.append(RegionSet(directory, overworld=False))

        self.regionsets.append(RegionSet(join(self.path, "entities")))
        for directory in glob(join(self.path, "DIM*/entities")):
            self.regionsets.append(RegionSet(directory, overworld=False))

        # level.dat
        # Let's scan level.dat here so we can extract the world name
        level_dat_path = join(self.path, "level.dat")
        if exists(level_dat_path):
            try:
                self.level_data = nbt.NBTFile(level_dat_path)["Data"]
                self.name = self.level_data["LevelName"].value
                self.scanned_level = ScannedDataFile(level_dat_path)
                self.scanned_level.status = c.DATAFILE_OK
            except Exception:
                self.name = None
                self.scanned_level = ScannedDataFile(level_dat_path)
                self.scanned_level.status = c.DATAFILE_UNREADABLE
        else:
            self.level_file = None
            self.level_data = None
            self.name = None
            self.scanned_level = ScannedDataFile(level_dat_path)
            self.scanned_level.status = c.DATAFILE_UNREADABLE

        # Player files
        self.datafilesets = []
        PLAYERS_DIRECTORY = 'playerdata'
        OLD_PLAYERS_DIRECTORY = ' players'
        STRUCTURES_DIRECTORY = 'data'

        self.players = DataFileSet(join(self.path, PLAYERS_DIRECTORY),
                                   "\nPlayer UUID files:\n")
        self.datafilesets.append(self.players)
        self.old_players = DataFileSet(join(self.path, OLD_PLAYERS_DIRECTORY),
                                       "\nOld format player files:\n")
        self.datafilesets.append(self.old_players)
        self.data_files = DataFileSet(join(self.path, STRUCTURES_DIRECTORY),
                                      "\nStructures and map data files:\n")
        self.datafilesets.append(self.data_files)

        # Does it look like a world folder?
        region_files = False
        for region_directory in self.regionsets:
            if region_directory:
                region_files = True
        if region_files:
            self.isworld = True
        else:
            self.isworld = False
        # TODO: Make a Exception for this! so we can use try/except

        # Set in scan.py, used in interactive.py
        self.scanned = False

    def __str__(self):
        counters = get_number_regions()
        text = "World information:\n"
        text += "   World path: {0}\n".format(self.path)
        text += "   World name: {0}\n".format(self.name)
        if c.LEVEL_DIR in counters :
            text += "   Region/Level files: {0}\n".format(counters[c.LEVEL_DIR])
        if c.POI_DIR in counters :
            text += "   POI files: {0}\n".format(counters[c.POI_DIR])
        if c.ENTITIES_DIR in counters :
            text += "   Entities files: {0}\n".format(counters[c.ENTITIES_DIR])
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    @property
    def has_problems(self):
        """ Returns True if the regionset has chunk or region problems and false otherwise.

        Return:
         - boolean -- A boolean, True if the world has any problems, false otherwise
        
        """

        if self.scanned_level.status in c.DATAFILE_PROBLEMS:
            return True

        for d in self.datafilesets:
            if d.has_problems:
                return True

        for r in self.regionsets:
            if r.has_problems:
                return True

        return False

    def get_number_regions(self):
        """ Returns a dictionnary with the number of regions files in this world
        
        Return:
         - counters -- An dictionnary with the amount of region files.
                
        """

        counters = {}
        for dim in self.regionsets:
            region_type = dim._get_region_type_directory()
            if not region_type in counters :
                counters[region_type] = 0
            counters[region_type] += len(dim)

        return counters

    def summary(self):
        """ Returns a string with a summary of the problems in this world.

        Return:
         - text -- A String with a human readable summary of all the problems in this world.

        This method calls the other summary() methods in RegionSet and DataSet. See these
        methods for more details.

        """

        final = ""

        # intro with the world name
        final += "{0:#^60}\n".format('')
        final += "{0:#^60}\n".format(" World name: {0} ".format(self.name))
        final += "{0:#^60}\n".format('')

        # leve.dat and data files
        final += "\nlevel.dat:\n"
        if self.scanned_level.status not in c.DATAFILE_PROBLEMS:
            final += "\t\'level.dat\' is readable\n"
        else:
            final += "\t[WARNING]: \'level.dat\' isn't readable, error: {0}\n".format(c.DATAFILE_STATUS_TEXT[self.scanned_level.status])

        sets = [self.players,
                self.old_players,
                self.data_files]

        for s in sets:
            final += s.title
            text = s.summary()
            final += text if text else "All files ok.\n"

        final += "\n"

        # chunk info
        chunk_info = ""
        for regionset in self.regionsets:
            title = regionset.get_name()
            final += "\n" + title + ":\n"

            # don't add text if there aren't broken chunks
            text = regionset.summary()
            chunk_info += text if text else ""
            final += chunk_info if chunk_info else "All the chunks are ok."

        return final

    def get_name(self):
        """ Returns a string with the name of the world.
        
        Return:
         - name -- String with either the world name as found in level.dat or the last
                   directory in the world path.

        """

        if self.name:
            return self.name
        else:
            n = split(self.path)
            if n[1] == '':
                n = split(n[0])[1]
            return n

    def count_regions(self, status=None):
        """ Returns an integer with the count of region files with status.

        Inputs:
         - status -- An integer from c.REGION_STATUSES to region files with that status.
                     For a list of status see REGION_STATUSES in constants.py

        Return:
         - counter -- An integer with the number of region files with the given status.

        """

        counter = 0
        for r in self.regionsets:
            counter += r.count_regions(status)
        return counter

    def count_chunks(self, status=None):
        """ Returns an integer with the count of chunks with 'status'.

        Inputs:
         - status -- An integer from c.CHUNK_STATUSES to count chunks with that status.
                     For a list of status see c.CHUNK_STATUSES.

        Return:
         - counter -- An integer with the number of chunks with the given status.

        """

        counter = 0
        for r in self.regionsets:
            count = r.count_chunks(status)
            counter += count
        return counter

    def replace_problematic_chunks(self, backup_worlds, status, entity_limit, delete_entities):
        """ Replaces problematic chunks using backups.
        
        Inputs:
         - backup_worlds -- A list of World objects to use as backups. Backup worlds will be used
                            in a ordered way.
         - status -- An integer indicating the status of chunks to be replaced.
                      See CHUNK_STATUSES in constants.py for a complete list.
         - entity_limit -- The threshold to consider a chunk with the status TOO_MANY_ENTITIES.
         - delete_entities -- Boolean indicating if the chunks with too_many_entities should have
                             their entities removed.
        
        Return:
         - counter -- An integer with the number of chunks replaced.

        """

        counter = 0
        scanned_regions = {}
        for regionset in self.regionsets:
            for backup in backup_worlds:
                # choose the correct regionset based on the dimension
                # folder name and the type name (region, POI and entities)
                for temp_regionset in backup.regionsets:
                    if ( temp_regionset._get_dimension_directory() == regionset._get_dimension_directory() and
                         temp_regionset._get_region_type_directory() == regionset._get_region_type_directory()):
                        b_regionset = temp_regionset
                        break

                # this don't need to be aware of region status, it just
                # iterates the list returned by list_chunks()
                bad_chunks = regionset.list_chunks(status)

                if ( bad_chunks and
                     b_regionset._get_dimension_directory() != regionset._get_dimension_directory() and
                     b_regionset._get_region_type_directory() != regionset._get_region_type_directory() ):
                    print("The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dim_type_string()))
                else:
                    for ck in bad_chunks:
                        global_coords = ck[0]
                        status_tuple = ck[1]
                        local_coords = _get_local_chunk_coords(*global_coords)
                        print("\n{0:-^60}".format(' New chunk to replace. Coords: x = {0}; z = {1} '.format(*global_coords)))

                        # search for the region file
                        backup_region_path, local_coords = b_regionset.locate_chunk(global_coords)
                        tofix_region_path, _ = regionset.locate_chunk(global_coords)
                        if exists(backup_region_path):
                            print("Backup region file found in:\n  {0}".format(backup_region_path))
                            # Scan the whole region file, pretty slow, but
                            # absolutely needed to detect sharing offset chunks
                            # The backups world doesn't change, check if the
                            # region_file is already scanned:
                            try:
                                coords = get_region_coords(split(backup_region_path)[1])
                                r = scanned_regions[coords]
                            except KeyError:
                                from .scan import scan_region_file
                                r = scan_region_file(ScannedRegionFile(backup_region_path), entity_limit, delete_entities)
                                scanned_regions[r.coords] = r
                            try:
                                status_tuple = r[local_coords]
                            except KeyError:
                                status_tuple = None

                            # Retrive the status from status_tuple
                            if status_tuple == None:
                                status = c.CHUNK_NOT_CREATED
                            else:
                                status = status_tuple[c.TUPLE_STATUS]

                            if status == c.CHUNK_OK:
                                backup_region_file = region.RegionFile(backup_region_path)
                                working_chunk = backup_region_file.get_chunk(local_coords[0], local_coords[1])

                                print("Replacing...")
                                # the chunk exists and is healthy, fix it!
                                tofix_region_file = region.RegionFile(tofix_region_path)
                                # first unlink the chunk, second write the chunk.
                                # unlinking the chunk is more secure and the only way to replace chunks with
                                # a shared offset without overwriting the good chunk
                                tofix_region_file.unlink_chunk(*local_coords)
                                tofix_region_file.write_chunk(local_coords[0], local_coords[1], working_chunk)
                                counter += 1
                                print("Chunk replaced using backup dir: {0}".format(backup.path))

                            else:
                                print("Can't use this backup directory, the chunk has the status: {0}".format(c.CHUNK_STATUS_TEXT[status]))
                                continue

                        else:
                            print("The region file doesn't exist in the backup directory: {0}".format(backup_region_path))

        return counter

    def remove_problematic_chunks(self, status):
        """ Removes all the chunks with the given status.
        
        Inputs:
         - status -- Integer with the chunk status to remove. See CHUNK_STATUSES in constants.py 
                     for a list of possible statuses.
        
        Return:
         - counter -- Integer with the number of chunks removed
        
        This method calls remove_problematic_chunks() in the RegionSets.

        """

        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_chunks(status)
        return counter

    def fix_problematic_chunks(self, status):
        """ Try to fix all the chunks with the given status.

        Inputs:
         - status -- Integer with the chunk status to remove. See CHUNK_STATUSES in constants.py 
                     for a list of possible statuses.
        
        Return:
         - counter -- Integer with the number of chunks fixed.

        This method calls remove_problematic_chunks() in the RegionSets.

        """

        counter = 0
        for regionset in self.regionsets:
            counter += regionset.fix_problematic_chunks(status)
        return counter

    def replace_problematic_regions(self, backup_worlds, status, entity_limit, delete_entities):
        """ Replaces problematic region files using backups.
        
        Inputs:
         - backup_worlds -- A list of World objects to use as backups. Backup worlds will be used
                            in a ordered way.
         - status -- An integer indicating the status of region files to be replaced.
                      See c.REGION_STATUSES for a complete list.
         - entity_limit -- The threshold to consider a chunk with the status TOO_MANY_ENTITIES.
                           (variable not used, just for inputs to be homogeneous)
         - delete_entities -- Boolean indicating if the chunks with too_many_entities should have
                             their entities removed. (variable not used, just for inputs to be homogeneous)
        Return:
         - counter -- An integer with the number of chunks replaced.

        Note: entity_limit and delete_entities are not really used here. They are just there to make all
        the methods homogeneous.

        """

        counter = 0
        for regionset in self.regionsets:
            for backup in backup_worlds:
                # choose the correct regionset based on the dimension
                # folder name and the type name (region, POI and entities)
                for temp_regionset in backup.regionsets:
                    if ( temp_regionset._get_dimension_directory() == regionset._get_dimension_directory() and
                         temp_regionset._get_region_type_directory() == regionset._get_region_type_directory()):
                        b_regionset = temp_regionset
                        break

                bad_regions = regionset.list_regions(status)
                if ( bad_chunks and
                     b_regionset._get_dimension_directory() != regionset._get_dimension_directory() and
                     b_regionset._get_region_type_directory() != regionset._get_region_type_directory() ):
                    print("The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dim_type_string()))
                else:
                    for r in bad_regions:
                        print("\n{0:-^60}".format(' New region file to replace! Coords {0} '.format(r.get_coords())))

                        # search for the region file

                        try:
                            backup_region_path = b_regionset[r.get_coords()].get_path()
                        except:
                            backup_region_path = None
                        tofix_region_path = r.get_path()

                        if backup_region_path != None and exists(backup_region_path):
                            print("Backup region file found in:\n  {0}".format(backup_region_path))
                            # check the region file, just open it.
                            try:
                                backup_region_file = region.RegionFile(backup_region_path)
                            except region.NoRegionHeader as e:
                                print("Can't use this backup directory, the error while opening the region file: {0}".format(e))
                                continue
                            except Exception as e:
                                print("Can't use this backup directory, unknown error: {0}".format(e))
                                continue
                            copy(backup_region_path, tofix_region_path)
                            print("Region file replaced!")
                            counter += 1
                        else:
                            print("The region file doesn't exist in the backup directory: {0}".format(backup_region_path))

        return counter

    def remove_problematic_regions(self, status):
        """ Removes all the regions files with the given status. See the warning!
        
        Inputs:
         - status -- Integer with the status of the region files to remove.
                     See REGION_STATUSES in constants. py for a list.
        
        Return:
         - counter -- An integer with the amount of removed region files.
        
        Warning! This is NOT the same as removing chunks, this WILL DELETE the region files 
        from the hard drive.

        """

        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_regions(status)
        return counter

    def remove_entities(self):
        """ Removes entities in chunks with the status TOO_MANY_ENTITIES. 

        Return:
         - counter -- Integer with the number of removed entities.

        """

        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the CHUNK_TOO_MANY_ENTITIES status of all the chunks in the RegionSet.
        
        This should be ran when the option entity limit is changed.

        """

        for regionset in self.regionsets:
            regionset.rescan_entities(options)

    def generate_report(self, standalone): 
        """ Generates a report with the results of the scan.
        
        Inputs:
         - standalone -- Boolean, if true the report will be a human readable String. If false the 
                         report will be a dictionary with all the counts of chunks and regions.
        
        Return if standalone = True:
         - text -- A human readable string of text with the results of the scan.
         
        Return if standlone = False:
         - chunk_counts -- Dictionary with all the counts of chunks for all the statuses. To read
                           it use the CHUNK_* constants. 
         - region_counts -- Dictionary with all the counts of region files for all the statuses. To read
                            it use the REGION_* constants.

        """

        # collect chunk data
        chunk_counts = {}
        has_chunk_problems = False
        for p in c.CHUNK_PROBLEMS:
            chunk_counts[p] = self.count_chunks(p)
            if chunk_counts[p] != 0:
                has_chunk_problems = True
        chunk_counts['TOTAL'] = self.count_chunks()

        # collect region data
        region_counts = {}
        has_region_problems = False
        for p in c.REGION_PROBLEMS:
            region_counts[p] = self.count_regions(p)
            if region_counts[p] != 0:
                has_region_problems = True
        region_counts['TOTAL'] = self.count_regions()

        # create a text string with a report of all found
        if standalone:
            text = ""

            # add all the player files with problems
            text += "\nUnreadable player files:\n"
            broken_players = [p for p in self.players._get_list() if p.status in c.DATAFILE_PROBLEMS]
            broken_players.extend([p for p in self.old_players._get_list() if p.status in c.DATAFILE_PROBLEMS])
            if broken_players:
                broken_player_files = [p.filename for p in broken_players]
                text += "\n".join(broken_player_files)
                text += "\n"
            else:
                text += "No problems found.\n"

            # Now all the data files
            text += "\nUnreadable data files:\n"
            broken_data_files = [d for d in self.data_files._get_list() if d.status in c.DATAFILE_PROBLEMS]
            if broken_data_files:
                broken_data_filenames = [p.filename for p in broken_data_files]
                text += "\n".join(broken_data_filenames)
                text += "\n"
            else:
                text += "No problems found.\n"

            # add all chunk info in a table format
            text += "\nChunk problems:\n"
            if has_chunk_problems:
                table_data = []
                table_data.append(['Problem', 'Count'])
                for p in c.CHUNK_PROBLEMS:
                    if chunk_counts[p] != 0:
                        table_data.append([c.CHUNK_STATUS_TEXT[p], chunk_counts[p]])
                table_data.append(['Total', chunk_counts['TOTAL']])
                text += table(table_data)
            else:
                text += "No problems found.\n"

            # add all region information
            text += "\n\nRegion problems:\n"
            if has_region_problems:
                table_data = []
                table_data.append(['Problem', 'Count'])
                for p in c.REGION_PROBLEMS:
                    if region_counts[p] != 0:
                        table_data.append([c.REGION_STATUS_TEXT[p], region_counts[p]])
                table_data.append(['Total', region_counts['TOTAL']])
                text += table(table_data)

            else:
                text += "No problems found."

            return text
        else:
            return chunk_counts, region_counts



def parse_paths(args):
    """ Parse a list of paths to and returns World and a RegionSet objects.
    
    Keywords arguments:
    args -- arguments as argparse got them

    Return:
    world_list -- A list of World objects
    RegionSet -- A RegionSet object with all the regionfiles found in args
    """

    # parese the list of region files and worlds paths
    world_list = []
    region_list = []
    warning = False
    for arg in args:
        if arg[-4:] == ".mca":
            region_list.append(arg)
        elif arg[-4:] == ".mcr": # ignore pre-anvil region files
            if not warning:
                print("Warning: Region-Fixer only works with anvil format region files. Ignoring *.mcr files")
                warning = True
        else:
            world_list.append(arg)

    # check if they exist
    region_list_tmp = []
    for f in region_list:
        if exists(f):
            if isfile(f):
                region_list_tmp.append(f)
            else:
                print("Warning: \"{0}\" is not a file. Skipping it and scanning the rest.".format(f))
        else:
            print("Warning: The region file {0} doesn't exists. Skipping it and scanning the rest.".format(f))
    region_list = region_list_tmp

    # init the world objects
    world_list = parse_world_list(world_list)

    return world_list, RegionSet(region_list = region_list)


def parse_world_list(world_path_list):
    """ Parses a world path list. Returns a list of World objects.

    Keywords arguments:
    world_path_list -- A list of string with paths where minecraft worlds are supposed to be

    Return:
    world_list -- A list of World objects using the paths from the input
 
    Parses a world path list checking if they exists and are a minecraft
    world folders. Returns a list of World objects. Prints errors for the 
    paths that are not minecraft worlds.
    """
    
    world_list = []
    for d in world_path_list:
        if exists(d):
            w = World(d)
            if w.isworld:
                world_list.append(w)
            else:
                print("Warning: The folder {0} doesn't look like a minecraft world. I'll skip it.".format(d))
        else:
            print("Warning: The folder {0} doesn't exist. I'll skip it.".format(d))
    return world_list


def parse_backup_list(world_backup_dirs):
    """ Generates a list with the input of backup dirs containing the
    world objects of valid world directories."""

    directories = world_backup_dirs.split(',')
    backup_worlds = parse_world_list(directories)
    return backup_worlds


def delete_entities(region_file, x, z):
    """ Removes entities in chunks with the status TOO_MANY_ENTITIES. 

    Keyword entities:
     - x -- Integer, X local coordinate of the chunk in the region files
     - z -- Integer, Z local coordinate of the chunk in the region files
     - region_file -- RegionFile object where the chunk is stored

    Return:
     - counter -- Integer with the number of removed entities.

    This function is used in scan.py.

    """

    chunk = region_file.get_chunk(x, z)
    empty_tag_list = nbt.TAG_List(nbt.TAG_Byte, '', 'Entities')
    if 'Level' in chunk : # Region file
        counter = len(chunk['Level']['Entities'])
        chunk['Level']['Entities'] = empty_tag_list
    elif 'Entities' in chunk : # Entities file (>=1.17)
        counter = len(chunk['Entities'])
        chunk['Entities'] = empty_tag_list
    else :
        raise AssertionError("Unrecognized chunk in delete_entities().")
    region_file.write_chunk(x, z, chunk)

    return counter


def _get_local_chunk_coords(chunkx, chunkz):
    """ Gives the chunk local coordinates from the global coordinates.
    
    Inputs:
     - chunkx -- Integer, X chunk global coordinate in the world.
     - chunkz -- Integer, Z chunk global coordinate in the world.
    
    Return:
     - x, z -- X and Z local coordinates of the chunk in the region file.

    """

    return chunkx % 32, chunkz % 32


def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk coordinates.
    
    Inputs:
     - chunkx -- Integer, X chunk global coordinate in the world.
     - chunkz -- Integer, Z chunk global coordinate in the world.
    
    Return:
     - region_name -- A string with the name of the region file where the chunk
                     should be.

    """

    regionX = chunkX // 32
    regionZ = chunkZ // 32

    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mca'

    return region_name


def get_chunk_data_coords(nbt_file):
    """ Gets and returns the coordinates stored in the NBT structure of the chunk.
    
    Inputs:
     - nbt_file -- An NBT file. From the nbt module.
     
    Return:
     - coordX, coordZ -- Integers with the X and Z global coordinates of the chunk.

    Do not confuse with the coordinates returned by get_global_coords, which could be different,
    marking this chunk as wrong_located.

    """

    # Region file
    if 'Level' in nbt_file :
        level = nbt_file.__getitem__('Level')

        coordX = level.__getitem__('xPos').value
        coordZ = level.__getitem__('zPos').value

    # Entities file :
    elif 'Entities' in nbt_file :
        coordX, coordZ = nbt_file.__getitem__('Position').value

    else :
        raise AssertionError("Unrecognized chunk in get_chunk_data_coords().")

    return coordX, coordZ


def get_region_coords(filename):
    """ Get and return a region file coordinates from path.
    
    Inputs:
     - filename -- Filename or path of the region file.
     
    Return:
     - coordX, coordZ -- X and z coordinates of the region file.

    """

    l = filename.split('.')
    coordX = int(l[1])
    coordZ = int(l[2])

    return coordX, coordZ


def get_global_chunk_coords(region_name, chunkX, chunkZ):
    """ Get and return a region file coordinates from path.
    
    Inputs:
     - region_name -- String with filename or path of the region file.
     - chunkX -- Integer, X local coordinate of the chunk
     - chunkZ -- Integer, Z local coordinate of the chunk

    Return:
     - coordX, coordZ -- X and z global coordinates of the
                         chunk in that region file.

    """

    regionX, regionZ = get_region_coords(region_name)
    chunkX += regionX * 32
    chunkZ += regionZ * 32

    return chunkX, chunkZ

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
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

import nbt.region as region
import nbt.nbt as nbt
from .util import table

from glob import glob
from os.path import join, split, exists
from os import remove
from shutil import copy

import time
from nbt.nbt import TAG_List

# Constants:

# 
# --------------
# Chunk related:
# --------------
# Used to mark the status of chunks:
CHUNK_NOT_CREATED = -1
CHUNK_OK = 0
CHUNK_CORRUPTED = 1
CHUNK_WRONG_LOCATED = 2
CHUNK_TOO_MANY_ENTITIES = 3
CHUNK_SHARED_OFFSET = 4
CHUNK_MISSING_ENTITIES_TAG = 5

# Chunk statuses 
CHUNK_STATUSES = [CHUNK_NOT_CREATED,
                  CHUNK_OK,
                  CHUNK_CORRUPTED,
                  CHUNK_WRONG_LOCATED,
                  CHUNK_TOO_MANY_ENTITIES,
                  CHUNK_SHARED_OFFSET,
                  CHUNK_MISSING_ENTITIES_TAG]

# Status that are considered problems
CHUNK_PROBLEMS = [CHUNK_CORRUPTED,
                  CHUNK_WRONG_LOCATED,
                  CHUNK_TOO_MANY_ENTITIES,
                  CHUNK_SHARED_OFFSET,
                  CHUNK_MISSING_ENTITIES_TAG]

# Text describing each chunk status
CHUNK_STATUS_TEXT = {CHUNK_NOT_CREATED: "Not created",
                     CHUNK_OK: "OK",
                     CHUNK_CORRUPTED: "Corrupted",
                     CHUNK_WRONG_LOCATED: "Wrong located",
                     CHUNK_TOO_MANY_ENTITIES: "Too many entities",
                     CHUNK_SHARED_OFFSET: "Sharing offset",
                     CHUNK_MISSING_ENTITIES_TAG: "Missing Entities tag"}

# arguments used in the options
CHUNK_PROBLEMS_ARGS = {CHUNK_CORRUPTED: 'corrupted',
                       CHUNK_WRONG_LOCATED: 'wrong',
                       CHUNK_TOO_MANY_ENTITIES: 'entities',
                       CHUNK_SHARED_OFFSET: 'sharing',
                       CHUNK_MISSING_ENTITIES_TAG: 'miss_tag'}

# used in some places where there is less space
CHUNK_PROBLEMS_ABBR = {CHUNK_CORRUPTED: 'c',
                       CHUNK_WRONG_LOCATED: 'w',
                       CHUNK_TOO_MANY_ENTITIES: 'tme',
                       CHUNK_SHARED_OFFSET: 'so',
                       CHUNK_MISSING_ENTITIES_TAG: 'mt'}

# Dictionary with possible solutions for the chunks problems,
# used to create options dynamically
# The possible solutions right now are:
CHUNK_SOLUTION_REMOVE = 51
CHUNK_SOLUTION_REPLACE = 52
CHUNK_SOLUTION_REMOVE_ENTITIES = 53

CHUNK_PROBLEMS_SOLUTIONS = {CHUNK_CORRUPTED: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE],
                       CHUNK_WRONG_LOCATED: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE],
                       CHUNK_TOO_MANY_ENTITIES: [CHUNK_SOLUTION_REMOVE_ENTITIES],
                       CHUNK_SHARED_OFFSET: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE],
                       CHUNK_MISSING_ENTITIES_TAG: [CHUNK_SOLUTION_REMOVE, CHUNK_SOLUTION_REPLACE]}

# list with problem, status-text, problem arg tuples
CHUNK_PROBLEMS_ITERATOR = []
for problem in CHUNK_PROBLEMS:
    CHUNK_PROBLEMS_ITERATOR.append((problem,
                                    CHUNK_STATUS_TEXT[problem],
                                    CHUNK_PROBLEMS_ARGS[problem]))

# Used to know where to look in a chunk status tuple
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1


# ---------------
# Region related:
# ---------------
# Used to mark the status of region files:
REGION_OK = 100
REGION_TOO_SMALL = 101
REGION_UNREADABLE = 102
REGION_UNREADABLE_PERMISSION_ERROR = 103

# Region statuses
REGION_STATUSES = [REGION_OK,
                   REGION_TOO_SMALL,
                   REGION_UNREADABLE,
                   REGION_UNREADABLE_PERMISSION_ERROR]

# Text describing each region status used to list all the problem at the end of the scan
REGION_STATUS_TEXT = {REGION_OK: "OK",
                      REGION_TOO_SMALL: "Too small",
                      REGION_UNREADABLE: "Unreadable IOError",
                      # This status differentiates IOError from a file that you don't have permission to access
                      # TODO: It would be better to open region files only in write mode when needed
                      REGION_UNREADABLE_PERMISSION_ERROR: "Permission error"}

# Status that are considered problems
REGION_PROBLEMS = [REGION_TOO_SMALL,
                   REGION_UNREADABLE,
                   REGION_UNREADABLE_PERMISSION_ERROR]

# arguments used in the options
REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL: 'too_small',
                        REGION_UNREADABLE: 'unreadable',
                        REGION_UNREADABLE_PERMISSION_ERROR: 'permission_error'}

# used in some places where there is less space
REGION_PROBLEMS_ABBR = {REGION_TOO_SMALL: 'ts',
                        REGION_UNREADABLE: 'ur',
                        REGION_UNREADABLE_PERMISSION_ERROR: 'pe'}

# Dictionary with possible solutions for the region problems,
# used to create options dynamically
# The possible solutions right now are:
REGION_SOLUTION_REMOVE = 151
REGION_SOLUTION_REPLACE = 152

REGION_PROBLEMS_SOLUTIONS = {REGION_TOO_SMALL: [REGION_SOLUTION_REMOVE, REGION_SOLUTION_REPLACE],
                       REGION_UNREADABLE: [REGION_SOLUTION_REMOVE, REGION_SOLUTION_REPLACE]}


# list with problem, status-text, problem arg tuples
REGION_PROBLEMS_ITERATOR = []
for problem in REGION_PROBLEMS:
    try:
        REGION_PROBLEMS_ITERATOR.append((problem,
                                         REGION_STATUS_TEXT[problem],
                                         REGION_PROBLEMS_ARGS[problem]))
    except KeyError:
        pass

REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL: 'too-small'}

# ------------------
# Data file related:
# ------------------
# Used to mark the status of data files:
DATAFILE_OK = 200
DATAFILE_UNREADABLE = 201


# Data files statuses 
DATAFILE_STATUSES = [DATAFILE_OK,
                  DATAFILE_UNREADABLE]

# Status that are considered problems
DATAFILE_PROBLEMS = [DATAFILE_UNREADABLE]

# Text describing each chunk status
DATAFILE_STATUS_TEXT = {DATAFILE_OK: "OK",
                        DATAFILE_UNREADABLE: "The data file cannot be read"}

# arguments used in the options
DATAFILE_PROBLEMS_ARGS = {DATAFILE_OK: 'OK',
                         DATAFILE_UNREADABLE: 'unreadable'}

# used in some places where there is less space
DATAFILE_PROBLEM_ABBR = {DATAFILE_OK: 'ok',
                         DATAFILE_UNREADABLE: 'ur'}

# Dictionary with possible solutions for the chunks problems,
# used to create options dynamically
# The possible solutions right now are:
DATAFILE_SOLUTION_REMOVE = 251

DATAFILE_PROBLEMS_SOLUTIONS = {DATAFILE_UNREADABLE:[DATAFILE_SOLUTION_REMOVE]}

# list with problem, status-text, problem arg tuples
DATAFILE_PROBLEMS_ITERATOR = []
for problem in DATAFILE_PROBLEMS:
    DATAFILE_PROBLEMS_ITERATOR.append((problem,
                                       DATAFILE_STATUS_TEXT[problem],
                                       DATAFILE_PROBLEMS_ARGS[problem]))

CHUNK_PROBLEMS_ITERATOR = []
for problem in CHUNK_PROBLEMS:
    CHUNK_PROBLEMS_ITERATOR.append((problem,
                                    CHUNK_STATUS_TEXT[problem],
                                    CHUNK_PROBLEMS_ARGS[problem]))



# Dimension names:
DIMENSION_NAMES = {"region": "Overworld",
                   "DIM1": "The End",
                   "DIM-1": "Nether"}


class InvalidFileName(IOError):
    pass


class ScannedDataFile(object):
    """ Stores all the information of a scanned data file. """
    def __init__(self, path=None):
        super().__init__()
        self.path = path
        if self.path and exists(self.path):
            self.filename = split(path)[1]
        else:
            self.filename = None
        # The status of the region file.
        self.status = None

    def __str__(self):
        text = "NBT file:" + str(self.filename) + "\n"
        text += "\tStatus:" + DATAFILE_STATUS_TEXT[self.status] + "\n"
        return text

    @property
    def oneliner_status(self):
        """ One line describing the status of the file. """
        return "File: \"" + self.filename + "\"; status: " + DATAFILE_STATUS_TEXT[self.status] 


class ScannedChunk(object):
    """ Stores all the results of the scan. Not used at the moment, it
        prette nice but takes an huge amount of memory. """
        # WARNING: This is here so I remember to not use objects as ScannedChunk
        # They take too much memory.


class ScannedRegionFile(object):
    """ Stores all the scan information for a region file """
    def __init__(self, path, time=None):
        # general region file info
        self.path = path
        self.filename = split(path)[1]
        self.folder = split(path)[0]
        self.x = self.z = None
        self.x, self.z = self.get_coords()
        self.coords = (self.x, self.z)

        # dictionary storing all the state tuples of all the chunks
        # in the region file
        self._chunks = {}

        # Dictionary containing counters to for all the chunks
        self._counts = {}
        for s in CHUNK_STATUSES:
            self._counts[s] = 0

        # time when the scan for this file finished
        self.scan_time = time

        # The status of the region file.
        self.status = None
        
        # has the file been scanned yet?
        self.scanned = False

    @property
    def oneliner_status(self):
        """ On line description of the status of the region file. """
        if self.scanned:
            status = self.status
            if status == REGION_OK: # summary with all found in scan
                stats = ""
                for s in CHUNK_PROBLEMS:
                    stats += "{0}:{1}, ".format(CHUNK_PROBLEMS_ABBR[s], self.count_chunks(s))
                stats += "t:{0}".format(self.count_chunks())
            else:
                stats = REGION_STATUS_TEXT[status]
        else:
            stats = "Not scanned"

        return stats

    def __str__(self):
        text = "Path: {0}".format(self.path)
        scanned = False
        if time:
            scanned = True
        text += "\nScanned: {0}".format(scanned)

        return text

    def __getitem__(self, key):
        return self._chunks[key]

    def __setitem__(self, key, value):
        self._chunks[key] = value
        self._counts[value[TUPLE_STATUS]] += 1

    def keys(self):
        return list(self._chunks.keys())

    @property
    def has_problems(self):
        """ Return True if the region file has problem in itself or in its chunks. """
        if self.status in REGION_PROBLEMS:
            return True
        for s in CHUNK_PROBLEMS:
            if self.count_chunks(s):
                return True
        return False

    def get_path(self):
        """ Returns the path of the region file. """
        return self.path

    def count_chunks(self, problem=None):
        """ Counts chunks in the region file with the given problem.
        
            If problem is omitted or None, counts all the chunks. Returns
            an integer with the counter. """

        if problem == None:
            c = 0
            for s in CHUNK_STATUSES: c += self._counts[s]
        else:
            c = self._counts[problem]

        return c

    def get_global_chunk_coords(self, chunkX, chunkZ):
        """ Takes the region filename and the chunk local
            coords and returns the global chunkcoords as integerss """

        regionX, regionZ = self.get_coords()
        chunkX += regionX * 32
        chunkZ += regionZ * 32

        return chunkX, chunkZ

    def get_coords(self):
        """ Splits the region filename (full pathname or just filename)
            and returns his region X and Z coordinates as integers. """
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

# TODO TODO TODO: This is dangerous! Running the method remove_problematic_chunks 
# without a problem will remove all the chunks in the region file!!
    def list_chunks(self, status=None):
        """ Returns a list of all the ScannedChunk objects of the chunks
            with the given status, if no status is omitted or None,
            returns all the existent chunks in the region file """

        l = []
        for c in list(self.keys()):
            t = self[c]
            if status == t[TUPLE_STATUS]:
                l.append((self.get_global_chunk_coords(*c), t))
            elif status == None:
                l.append((self.get_global_chunk_coords(*c), t))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks. The summary
            is a string with region file, global coords, local coords,
            and status of every problematic chunk. """
        text = ""
        if self.status in REGION_PROBLEMS:
            text += " |- This region has status: {0}.\n".format(REGION_STATUS_TEXT[self.status])
        else:
            for c in list(self.keys()):
                if self[c][TUPLE_STATUS] not in CHUNK_PROBLEMS: 
                    continue
                status = self[c][TUPLE_STATUS]
                h_coords = c
                g_coords = self.get_global_chunk_coords(*h_coords)
                text += " |-+-Chunk coords: header {0}, global {1}.\n".format(h_coords, g_coords)
                text += " | +-Status: {0}\n".format(CHUNK_STATUS_TEXT[status])
                if self[c][TUPLE_STATUS] == CHUNK_TOO_MANY_ENTITIES:
                    text += " | +-No. entities: {0}\n".format(self[c][TUPLE_NUM_ENTITIES])
                text += " |\n"

        return text

    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a
            counter with the number of deleted chunks. """

        counter = 0
        bad_chunks = self.list_chunks(problem)
        for c in bad_chunks:
            global_coords = c[0]
            status_tuple = c[1]
            local_coords = _get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            region_file.unlink_chunk(*local_coords)
            counter += 1
            # create the new status tuple
            #                    (num_entities, chunk status)
            self[local_coords] = (0           , CHUNK_NOT_CREATED)

        return counter

    def fix_problematic_chunks(self, problem):
        """ This fixes problems in chunks that can be somehow easy to fix.
        
        Right now it only fixes chunks missing the TAG_List Entities.
        """
        # TODO: it seems having the Entities TAG missing is just a little part. Some of the
        # chunks have like 3 or 4 tag missing from the NBT structure. 
        counter = 0
        bad_chunks = self.list_chunks(problem)
        for c in bad_chunks:
            global_coords = c[0]
            local_coords = _get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            chunk = region_file.get_chunk(*local_coords)
            # The arguments to create the empty TAG_List have been somehow extracted by comparing
            # the tag list from a healthy chunk with the one created by nbt
            chunk['Level']['Entities'] = TAG_List(name='Entities', type=nbt._TAG_End)
            region_file.write_chunk(local_coords[0],local_coords[1], chunk)
            counter += 1
            # create the new status tuple
            #                    (num_entities, chunk status)
            self[local_coords] = (0           , CHUNK_NOT_CREATED)

        return counter


    def remove_entities(self):
        """ Removes all the entities in chunks with the problematic
            CHUNK_TOO_MANY_ENTITIES that are in this region file.
            Returns a counter of all the removed entities. """
        problem = CHUNK_TOO_MANY_ENTITIES
        counter = 0
        bad_chunks = self.list_chunks(problem)
        for c in bad_chunks:
            global_coords = c[0]
            status_tuple = c[1]
            local_coords = _get_local_chunk_coords(*global_coords)
            counter += self.remove_chunk_entities(*local_coords)
            # create new status tuple:
            #                    (num_entities, chunk status)
            self[local_coords] = (0           , CHUNK_OK)
        return counter

    def remove_chunk_entities(self, x, z):
        """ Takes a chunk coordinates, opens the chunk and removes all
            the entities in it. Return an integer with the number of
            entities removed"""
        region_file = region.RegionFile(self.path)
        chunk = region_file.get_chunk(x,z)
        counter = len(chunk['Level']['Entities'])
        empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')
        chunk['Level']['Entities'] = empty_tag_list
        region_file.write_chunk(x, z, chunk)

        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the region file when
            the the option entity limit is changed. """
        for c in list(self.keys()):
            # for safety reasons use a temporary list to generate the
            # new tuple
            t = [0,0]
            if self[c][TUPLE_STATUS] in (CHUNK_TOO_MANY_ENTITIES, CHUNK_OK):
                # only touch the ok chunks and the too many entities chunk
                if self[c][TUPLE_NUM_ENTITIES] > options.entity_limit:
                    # now it's a too many entities problem
                    t[TUPLE_NUM_ENTITIES] = self[c][TUPLE_NUM_ENTITIES]
                    t[TUPLE_STATUS] = CHUNK_TOO_MANY_ENTITIES

                elif self[c][TUPLE_NUM_ENTITIES] <= options.entity_limit:
                    # the new limit says it's a normal chunk
                    t[TUPLE_NUM_ENTITIES] = self[c][TUPLE_NUM_ENTITIES]
                    t[TUPLE_STATUS] = CHUNK_OK

                self[c] = tuple(t)


class DataSet(object):
    """ Stores data items to be scanned by AsyncScanner in scan.py. 

    typevalue is the type of the class to store in the set. When setting it will be
    asserted if it is of that type

    The data should be in a dictionary and should be accessible through the 
    methods __getitem__, __setitem__. The methods, _get_list, __len__ are also used.

    _replace_in_data_structure should be created because during the scan the 
    different processes create copies of the original data, so replacing it in
    the original data set is mandatory.

    _update_counts makes sure that the DataSet stores all the counts and that
    it is not needed to loop through all of them to know the real count.

    has_problems should return True only if any element of the set has problems

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
        assert(self._typevalue == type(value))
        self._set[key] = value
        self._update_counts(value)

    def __len__(self):
        return len(self._set)
    
    # mandatory implementation methods
    def summary(self):
        """ Return a summary of problems found in this set. """
        raise NotImplemented

    @property
    def has_problems(self):
        """ Returns True if the scanned set has problems. """
        raise NotImplemented

    def _replace_in_data_structure(self, data, key):
        """ For multiprocessing. Replaces the data in the set with the new data.
        
        Child scanning processes make copies of the ScannedRegion/DataFile when they scan them.
        The AsyncScanner will call this function so the ScannedRegion/DataFile is stored
        in the set properly.
        """
        raise NotImplemented

    def _update_counts(self, s):
        """ This functions is used by __set__ to update the counters. """
        raise NotImplemented


class DataFileSet(DataSet):
    """ Any scanneable set should derive from this.

    DataSets are scanned using scan.AsyncScanner
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
        for s in DATAFILE_STATUSES:
            self._counts[s] = 0

    @property
    def has_problems(self):
        """ Returns True if the dataset has problems and false otherwise. """
        for d in self._set.values():
            if d.status in DATAFILE_PROBLEMS:
                return True
        return False

    def _replace_in_data_structure(self, data):
        self._set[data.path] = data

    def _update_counts(self, s):
        assert(type(s) == self._typevalue)
        self._counts[s.status] += 1

    def count_datafiles(self, status):
        pass

    def summary(self):
        """ Return a summary of problems found in this set. """
        text = ""
        bad_data_files = [i for i in list(self._set.values()) if i.status in DATAFILE_PROBLEMS]
        for f in bad_data_files:
            text += "\t" + f.oneliner_status
            text += "\n"
        return text


class RegionSet(DataSet):
    """Stores an arbitrary number of region files and the scan results.
        Inits with a list of region files. The regions dict is filled
        while scanning with ScannedRegionFiles and ScannedChunks."""
    def __init__(self, regionset_path=None, region_list=[]):
        DataSet.__init__(self, ScannedRegionFile)
        if regionset_path:
            self.path = regionset_path
            self.region_list = glob(join(self.path, "r.*.*.mca"))
        else:
            self.path = None
            self.region_list = region_list
        self._set = {}
        for path in self.region_list:
            try:
                r = ScannedRegionFile(path)
                self._set[r.get_coords()] = r

            except InvalidFileName as e:
                print("Warning: The file {0} is not a valid name for a region. I'll skip it.".format(path))
        
        # region and chunk counters with all the data from the scan
        self._region_counters = {}
        for status in REGION_STATUSES:
            self._region_counters[status] = 0
        
        self._chunk_counters = {}
        for status in CHUNK_STATUSES:
            self._chunk_counters[status] = 0
        
        # has this regionset been scanned?
        self.scanned = False

    def get_name(self):
        """ Return a string with a representative name for the regionset
        
        If the regionset is a dimension its name is returned, if not the directory and
        if there is no name or "" if there is nothing to fall back
        """

        dim_directory = self._get_dimension_directory()
        if dim_directory:
            try:
                return DIMENSION_NAMES[dim_directory]
            except:
                return dim_directory
        else:
            return ""

    def _update_counts(self, scanned_regionfile):
        """ Updates the counters of the regionset with the new regionfile. """

        assert(type(scanned_regionfile) == ScannedRegionFile)
        
        self._region_counters[scanned_regionfile.status] += 1

        for status in CHUNK_STATUSES:
            self._chunk_counters[status] += scanned_regionfile.count_chunks(status)

    def _get_dimension_directory(self):
        """ Returns a string with the directory of the dimension, None
        if there is no such a directory and the regionset is composed
        of sparse region files. """
        if self.path:
            rest, region = split(self.path)
            rest, dim_path = split(rest)
            if dim_path == "":
                dim_path = split(rest)[1]
            return dim_path
        else:
            return None

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

        for s in REGION_PROBLEMS:
            if self.count_regions(s):
                return True
        
        for s in CHUNK_PROBLEMS:
            if self.count_chunks(s):
                return True
        
        return False

    def keys(self):
        return list(self._set.keys())

    def list_regions(self, status=None):
        """ Returns a list of all the ScannedRegionFile objects stored
            in the RegionSet with status. If status = None it returns
            all the objects."""

        if status == None:
            return list(self._set.values())
        t = []
        for coords in list(self._set.keys()):
            r = self._set[coords]
            if r.status == status:
                t.append(r)
        return t

    def count_regions(self, status=None):
        """ Return the number of region files with status. If none
            returns the number of region files in this regionset.
            Possible status are: empty, too_small """
        
        #=======================================================================
        # counter = 0
        # for r in list(self.keys()):
        #     if status == self[r].status:
        #         counter += 1
        #     elif status == None:
        #         counter += 1
        #=======================================================================
        counter = 0
        if status == None:
            for s in REGION_STATUSES:
                counter += self._region_counters[s]
        else:        
            counter = self._region_counters[status]

        
        return counter

    def count_chunks(self, problem=None):
        """ Returns the number of chunks with the given problem. If
            problem is None returns the number of chunks. """

        c = 0
        if problem == None:
            for s in CHUNK_STATUSES:
                c += self._chunk_counters[s]
        else:
            c = self._chunk_counters[problem]
        
        return c

    def list_chunks(self, status=None):
        """ Returns a list of the ScannedChunk objects of the chunks
            with the given status. If status = None returns all the
            chunks. """
        l = []
        for r in list(self.keys()):
            l.extend(self[r].list_chunks(status))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks in this
            regionset. The summary is a string with global coords,
            local coords, data coords and status. """
        text = ""
        for r in list(self.keys()):
            if not self[r].has_problems:
                continue
            text += "Region file: {0}\n".format(self[r].filename)
            text += self[r].summary()
            text += " +\n\n"
        return text

    def locate_chunk(self, global_coords):
        """ Takes the global coordinates of a chunk and returns the
            region filename and the local coordinates of the chunk or
            None if it doesn't exits in this RegionSet """

        filename = self.path + get_chunk_region(*global_coords)
        local_coords = _get_local_chunk_coords(*global_coords)

        return filename, local_coords

    def locate_region(self, coords):
        """ Returns a string with the path of the region file with
            the given coords in this regionset or None if not found. """

        x, z = coords
        region_name = 'r.' + str(x) + '.' + str(z) + '.mca'

        return region_name

    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a
            counter with the number of deleted chunks. """

        counter = 0
        if self.count_chunks():
            print(' Deleting chunks in region set \"{0}\":'.format(self._get_dimension_directory()))
            for r in list(self._set.keys()):
                counter += self._set[r].remove_problematic_chunks(problem)
            print("Removed {0} chunks in this regionset.\n".format(counter))

        return counter

    def fix_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a
            counter with the number of deleted chunks. """

        counter = 0
        if self.count_chunks():
            print(' Repairing chunks in region set \"{0}\":'.format(self._get_dimension_directory()))
            for r in list(self._set.keys()):
                counter += self._set[r].fix_problematic_chunks(problem)
            print("Repaired {0} chunks in this regionset.\n".format(counter))

        return counter

    def remove_entities(self):
        """ Removes entities in chunks with the status
            TOO_MANY_ENTITIES. """
        counter = 0
        for r in list(self._set.keys()):
            counter += self._set[r].remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the regionset when
            the option entity limit is changed. """
        for r in list(self.keys()):
            self[r].rescan_entities(options)

    
    def generate_report(self, standalone):
        """ Generates a report with the results of the scan. The report
        will include information about chunks and regions. 
        
        If standalone is true it will return a string of text with the 
        results of the scan.
        
        If standalone is false it will return a dictionary with all the counts of chunks
        and regions, to use the dictionary use the variables defined in the start of this
        file. The variables are named CHUNK_*
        """

        # collect chunk data
        chunk_counts = {}
        has_chunk_problems = False
        for p in CHUNK_PROBLEMS:
            chunk_counts[p] = self.count_chunks(p)
            if chunk_counts[p] != 0:
                has_chunk_problems = True
        chunk_counts['TOTAL'] = self.count_chunks()
        
        # collect region data
        region_counts = {}
        has_region_problems = False
        for p in REGION_PROBLEMS:
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
                table_data.append(['Problem','Count'])
                for p in CHUNK_PROBLEMS:
                    if chunk_counts[p] is not 0:
                        table_data.append([CHUNK_STATUS_TEXT[p],chunk_counts[p]])
                table_data.append(['Total', chunk_counts['TOTAL']])
                text += table(table_data)
            else:
                text += "No problems found.\n"

            # add all region information
            text += "\n\nRegion problems:\n"
            if has_region_problems:
                table_data = []
                table_data.append(['Problem','Count'])
                for p in REGION_PROBLEMS:
                    if region_counts[p] is not 0:
                        table_data.append([REGION_STATUS_TEXT[p],region_counts[p]])
                table_data.append(['Total', region_counts['TOTAL']])
                text += table(table_data)
            
            else:
                text += "No problems found."

            return text
        else:
            return chunk_counts, region_counts
    def remove_problematic_regions(self, problem):
        """ Removes all the regions files with the given problem.
            This is NOT the same as removing chunks, this WILL DELETE
            the region files from the hard drive. """
        counter = 0
        for r in self.list_regions(problem):
            remove(r.get_path())
            counter += 1
        return counter


class World(object):
    """ This class stores all the info needed of a world, and once
    scanned, stores all the problems found. It also has all the tools
    needed to modify the world."""

    def __init__(self, world_path):
        self.path = world_path

        # list with RegionSets
        self.regionsets = []

        self.regionsets.append(RegionSet(join(self.path, "region/")))
        for directory in glob(join(self.path, "DIM*/region")):
            self.regionsets.append(RegionSet(join(self.path, directory)))

        # level.dat
        # Let's scan level.dat here so we can extract the world name
        level_dat_path = join(self.path, "level.dat")
        if exists(level_dat_path):
            try:
                self.level_data = nbt.NBTFile(level_dat_path)["Data"]
                self.name = self.level_data["LevelName"].value
                self.scanned_level = ScannedDataFile(level_dat_path)
                self.scanned_level.status = DATAFILE_OK
            except Exception as e:
                self.name = None
                self.scanned_level = ScannedDataFile(level_dat_path)
                self.scanned_level.status = DATAFILE_UNREADABLE
        else:
            self.level_file = None
            self.level_data = None
            self.name = None
            self.scanned_level = ScannedDataFile(level_dat_path)
            self.scanned_level.status = DATAFILE_UNREADABLE

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
        text = "World information:\n"
        text += "   World path: {0}\n".format(self.path)
        text += "   World name: {0}\n".format(self.name)
        text += "   Region files: {0}\n".format(self.get_number_regions())
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    @property
    def has_problems(self):
        """ Returns True if the regionset has chunk or region problems and false otherwise. """

        if self.scanned_level.status in DATAFILE_PROBLEMS:
            return True
        
        for d in self.datafilesets:
            if d.has_problems:
                return True
        
        for r in self.regionsets:
            if r.has_problems:
                return True
        
        return False

    def get_number_regions(self):
        """ Returns a integer with the number of regions in this world"""
        counter = 0
        for dim in self.regionsets:
            counter += len(dim)

        return counter

    def summary(self):
        """ Returns a text string with a summary of all the problems
            found in the world object."""
        final = ""

        # intro with the world name
        final += "{0:#^60}\n".format('')
        final += "{0:#^60}\n".format(" World name: {0} ".format(self.name))
        final += "{0:#^60}\n".format('')

        # leve.dat and data files
        final += "\nlevel.dat:\n"
        if self.scanned_level.status not in DATAFILE_PROBLEMS:
            final += "\t\'level.dat\' is readable\n"
        else:
            final += "\t[WARNING]: \'level.dat\' isn't readable, error: {0}\n".format(DATAFILE_STATUS_TEXT[self.scanned_level.status])

        sets = [self.players,
                self.old_players,
                self.data_files]

        for set in sets:
            final += set.title
            text = set.summary()
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
        """ Returns a string with the name as found in level.dat or
            with the world folder's name. """
        if self.name:
            return self.name
        else:
            n = split(self.path) 
            if n[1] == '':
                n = split(n[0])[1]
            return n

    def count_regions(self, status = None):
        """ Returns a number with the count of region files with
            status. """
        counter = 0
        for r in self.regionsets:
            counter += r.count_regions(status)
        return counter

    def count_chunks(self, status = None):
        """ Counts problems  """
        counter = 0
        for r in self.regionsets:
            count = r.count_chunks(status)
            counter += count
        return counter

    def replace_problematic_chunks(self, backup_worlds, problem, entity_limit, delete_entities):
        """ Takes a list of world objects and a problem value and try
            to replace every chunk with that problem using a working
            chunk from the list of world objects. It uses the world
            objects in left to right order. """

        counter = 0
        scanned_regions = {}
        for regionset in self.regionsets:
            for backup in backup_worlds:
                # choose the correct regionset based on the dimension
                # folder name
                for temp_regionset in backup.regionsets:
                    if temp_regionset._get_dimension_directory() == regionset._get_dimension_directory():
                        b_regionset = temp_regionset
                        break

                # this don't need to be aware of region status, it just
                # iterates the list returned by list_chunks()
                bad_chunks = regionset.list_chunks(problem)

                if bad_chunks and b_regionset._get_dimension_directory() != regionset._get_dimension_directory():
                    print("The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dimension_directory()))
                else:
                    for c in bad_chunks:
                        global_coords = c[0]
                        status_tuple = c[1]
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
                                status = CHUNK_NOT_CREATED
                            else:
                                status = status_tuple[TUPLE_STATUS]

                            if status == CHUNK_OK:
                                backup_region_file = region.RegionFile(backup_region_path)
                                working_chunk = backup_region_file.get_chunk(local_coords[0],local_coords[1])

                                print("Replacing...")
                                # the chunk exists and is healthy, fix it!
                                tofix_region_file = region.RegionFile(tofix_region_path)
                                # first unlink the chunk, second write the chunk.
                                # unlinking the chunk is more secure and the only way to replace chunks with 
                                # a shared offset withou overwriting the good chunk
                                tofix_region_file.unlink_chunk(*local_coords)
                                tofix_region_file.write_chunk(local_coords[0], local_coords[1],working_chunk)
                                counter += 1
                                print("Chunk replaced using backup dir: {0}".format(backup.path))

                            else:
                                print("Can't use this backup directory, the chunk has the status: {0}".format(CHUNK_STATUS_TEXT[status]))
                                continue

                        else:
                            print("The region file doesn't exist in the backup directory: {0}".format(backup_region_path))

        return counter


    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_chunks(problem)
        return counter

    def fix_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.fix_problematic_chunks(problem)
        return counter

    def replace_problematic_regions(self, backup_worlds, problem, entity_limit, delete_entities):
        """ Replaces region files with the given problem using a backup
            directory. """
        counter = 0
        for regionset in self.regionsets:
            for backup in backup_worlds:
                # choose the correct regionset based on the dimension
                # folder name
                for temp_regionset in backup.regionsets:
                    if temp_regionset._get_dimension_directory() == regionset._get_dimension_directory():
                        b_regionset = temp_regionset
                        break

                bad_regions = regionset.list_regions(problem)
                if bad_regions and b_regionset._get_dimension_directory() != regionset._get_dimension_directory():
                    print("The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dimension_directory()))
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

    def remove_problematic_regions(self, problem):
        """ Removes all the regions files with the given problem.
            This is NOT the same as removing chunks, this WILL DELETE
            the region files from the hard drive. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_regions(problem)
        return counter

    def remove_entities(self):
        """ Delete all the entities in the chunks that have more than
            entity-limit entities. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the world when the
            option entity limit is changed. """
        for regionset in self.regionsets:
            regionset.rescan_entities(options)

    def generate_report(self, standalone):
        """ Generates a report with the results of the scan. The report
        will include information about data structures (.dat files), 
        player files, chunks and regions. 
        
        If standalone is true it will return a string of text with the 
        results of the scan.
        
        If standalone is false it will return a dictionary with all the counts,
        to use the dictionary use the variables defined in the start of this
        file. The variables are named CHUNK_*. Note that right now doesn't return
        information about the data files.
        """

        # collect chunk data
        chunk_counts = {}
        has_chunk_problems = False
        for p in CHUNK_PROBLEMS:
            chunk_counts[p] = self.count_chunks(p)
            if chunk_counts[p] != 0:
                has_chunk_problems = True
        chunk_counts['TOTAL'] = self.count_chunks()
        
        # collect region data
        region_counts = {}
        has_region_problems = False
        for p in REGION_PROBLEMS:
            region_counts[p] = self.count_regions(p)
            if region_counts[p] != 0:
                has_region_problems = True
        region_counts['TOTAL'] = self.count_regions()
        
        # create a text string with a report of all found
        if standalone:
            text = ""

            # add all the player files with problems
            text += "\nUnreadable player files:\n"
            broken_players = [p for p in self.players._get_list() if p.status in DATAFILE_PROBLEMS]
            broken_players.extend([p for p in self.old_players._get_list() if p.status in DATAFILE_PROBLEMS])
            if broken_players:
                broken_player_files = [p.filename for p in broken_players]
                text += "\n".join(broken_player_files)
                text += "\n"
            else:
                text += "No problems found.\n"

            # Now all the data files
            text += "\nUnreadable data files:\n"
            broken_data_files = [d for d in self.data_files._get_list() if d.status in DATAFILE_PROBLEMS]
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
                table_data.append(['Problem','Count'])
                for p in CHUNK_PROBLEMS:
                    if chunk_counts[p] is not 0:
                        table_data.append([CHUNK_STATUS_TEXT[p],chunk_counts[p]])
                table_data.append(['Total', chunk_counts['TOTAL']])
                text += table(table_data)
            else:
                text += "No problems found.\n"

            # add all region information
            text += "\n\nRegion problems:\n"
            if has_region_problems:
                table_data = []
                table_data.append(['Problem','Count'])
                for p in REGION_PROBLEMS:
                    if region_counts[p] is not 0:
                        table_data.append([REGION_STATUS_TEXT[p],region_counts[p]])
                table_data.append(['Total', region_counts['TOTAL']])
                text += table(table_data)
            
            else:
                text += "No problems found."

            return text
        else:
            return chunk_counts, region_counts



def delete_entities(region_file, x, z):
    """ This function is used while scanning the world in scan.py! Takes
        a region file obj and a local chunks coords and deletes all the
        entities in that chunk. """
    chunk = region_file.get_chunk(x,z)
    counter = len(chunk['Level']['Entities'])
    empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')
    chunk['Level']['Entities'] = empty_tag_list
    region_file.write_chunk(x, z, chunk)

    return counter


def _get_local_chunk_coords(chunkx, chunkz):
    """ Takes the chunk global coords and returns the local coords """
    return chunkx % 32, chunkz % 32

def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk
        coords """

    regionX = chunkX // 32
    regionZ = chunkZ // 32

    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mca'

    return region_name

def get_chunk_data_coords(nbt_file):
    """ Gets the coords stored in the NBT structure of the chunk.

        Takes an nbt obj and returns the coords as integers.
        Don't confuse with get_global_chunk_coords! """

    level = nbt_file.__getitem__('Level')

    coordX = level.__getitem__('xPos').value
    coordZ = level.__getitem__('zPos').value

    return coordX, coordZ

def get_region_coords(filename):
    """ Splits the region filename (full pathname or just filename)
        and returns his region X and Z coordinates as integers. """

    l = filename.split('.')
    coordX = int(l[1])
    coordZ = int(l[2])

    return coordX, coordZ

def get_global_chunk_coords(region_name, chunkX, chunkZ):
    """ Takes the region filename and the chunk local
        coords and returns the global chunkcoords as integerss. This 
        version does exactly the same as the method in 
        ScannedRegionFile. """

    regionX, regionZ = get_region_coords(region_name)
    chunkX += regionX*32
    chunkZ += regionZ*32

    return chunkX, chunkZ

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
from util import table

from glob import glob
from os.path import join, split, exists
from os import remove
from shutil import copy

import time

# Constants:
# Used to mark the status of a chunks:
CHUNK_NOT_CREATED = -1
CHUNK_OK = 0
CHUNK_CORRUPTED = 1
CHUNK_WRONG_LOCATED = 2
CHUNK_TOO_MANY_ENTITIES = 3
CHUNK_SHARED_OFFSET = 4
CHUNK_STATUS_TEXT = {CHUNK_NOT_CREATED:"Not created",
                    CHUNK_OK:"OK",
                    CHUNK_CORRUPTED:"Corrupted",
                    CHUNK_WRONG_LOCATED:"Wrong located",
                    CHUNK_TOO_MANY_ENTITIES:"Too many entities",
                    CHUNK_SHARED_OFFSET:"Sharing offset"}

CHUNK_PROBLEMS = [CHUNK_CORRUPTED, CHUNK_WRONG_LOCATED, CHUNK_TOO_MANY_ENTITIES, CHUNK_SHARED_OFFSET]

CHUNK_PROBLEMS_ARGS = {CHUNK_CORRUPTED:'corrupted',CHUNK_WRONG_LOCATED:'wrong',CHUNK_TOO_MANY_ENTITIES:'entities',CHUNK_SHARED_OFFSET:'sharing'}
# list with problem status-text tuples
CHUNK_PROBLEMS_ITERATOR = []
for problem in CHUNK_PROBLEMS:
    CHUNK_PROBLEMS_ITERATOR.append((problem, CHUNK_STATUS_TEXT[problem], CHUNK_PROBLEMS_ARGS[problem]))



# Used to mark the status of region files:
REGION_OK = 10
REGION_TOO_SMALL = 11
REGION_UNREADABLE = 12
REGION_STATUS_TEXT = {REGION_OK: "Ok", REGION_TOO_SMALL: "Too small", REGION_UNREADABLE: "Unreadable"}

REGION_PROBLEMS = [REGION_TOO_SMALL]
REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL: 'too-small'}

# list with problem status-text tuples
REGION_PROBLEMS_ITERATOR = []
for problem in REGION_PROBLEMS:
    try:
        REGION_PROBLEMS_ITERATOR.append((problem, REGION_STATUS_TEXT[problem], REGION_PROBLEMS_ARGS[problem]))
    except KeyError:
        pass

REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL:'too-small'}

# Used to know where to look in a chunk status tuple
#~ TUPLE_COORDS = 0
#~ TUPLE_DATA_COORDS = 0
#~ TUPLE_GLOBAL_COORDS = 2
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1

# Dimension names:
DIMENSION_NAMES = { "region":"Overworld", "DIM1":"The End", "DIM-1":"Nether" }

class ScannedDatFile(object):
    def __init__(self, path = None, readable = None, status_text = None):
        self.path = path
        if self.path and exists(self.path):
            self.filename = split(path)[1]
        else:
            self.filename = None
        self.readable = readable
        self.status_text = status_text

    def __str__(self):
        text = "NBT file:" + str(self.path) + "\n"
        text += "\tReadable:" + str(self.readable) + "\n"
        return text

class ScannedChunk(object):
    """ Stores all the results of the scan. Not used at the moment, it
        prette nice but takes an huge amount of memory. """
        # WARNING: not used at the moment, it probably has bugs ans is
        # outdated
        # The problem with it was it took too much memory. It has been
        # remplaced with a tuple
    def __init__(self, header_coords, global_coords = None, data_coords = None, status = None, num_entities = None, scan_time = None, region_path = None):
        """ Inits the object with all the scan information. """
        self.h_coords = header_coords
        self.g_coords = global_coords
        self.d_coords = data_coords
        self.status = status
        self.status_text = None
        self.num_entities = num_entities
        self.scan_time = scan_time
        self.region_path = region_path

    def __str__(self):
        text = "Chunk with header coordinates:" + str(self.h_coords) + "\n"
        text += "\tData coordinates:" + str(self.d_coords) + "\n"
        text +="\tGlobal coordinates:" + str(self.g_coords) + "\n"
        text += "\tStatus:" + str(self.status_text) + "\n"
        text += "\tNumber of entities:" + str(self.num_entities) + "\n"
        text += "\tScan time:" + time.ctime(self.scan_time) + "\n"
        return text

    def get_path():
        """ Returns the path of the region file. """
        return self.region_path

    def rescan_entities(self, options):
        """ Updates the status of the chunk when the the option
            entity limit is changed. """
        if self.num_entities >= options.entity_limit:
            self.status = CHUNK_TOO_MANY_ENTITIES
            self.status_text = CHUNK_STATUS_TEXT[CHUNK_TOO_MANY_ENTITIES]
        else:
            self.status = CHUNK_OK
            self.status_text = CHUNK_STATUS_TEXT[CHUNK_OK]

class ScannedRegionFile(object):
    """ Stores all the scan information for a region file """
    def __init__(self, filename, corrupted = 0, wrong = 0, entities_prob = 0, shared_offset = 0, chunks = 0, status = 0, time = None):
        # general region file info
        self.path = filename
        self.filename = split(filename)[1]
        self.folder = split(filename)[0]
        self.x = self.z = None
        self.x, self.z = self.get_coords()
        self.coords = (self.x, self.z)

        # dictionary storing all the state tuples of all the chunks
        # in the region file
        self.chunks = {}

        # TODO: these values aren't really used.
        # count_chunks() is used instead.
        # counters with the number of chunks
        self.corrupted_chunks = corrupted
        self.wrong_located_chunks = wrong
        self.entities_prob = entities_prob
        self.shared_offset = shared_offset
        self.chunk_count = chunks

        # time when the scan for this file finished
        self.scan_time = time

        # The status of the region file. At the moment can be OK,
        # TOO SMALL or UNREADABLE see the constants at the start
        # of the file.
        self.status = status

    def __str__(self):
        text = "Path: {0}".format(self.path)
        scanned = False
        if time:
            scanned = True
        text += "\nScanned: {0}".format(scanned)

        return text

    def __getitem__(self, key):
        return self.chunks[key]

    def __setitem__(self, key, value):
        self.chunks[key] = value

    def keys(self):
        return self.chunks.keys()

    def get_counters(self):
        """ Returns integers with all the problem counters in this
            region file. The order is corrupted, wrong located, entities
            shared header, total chunks """
        return self.corrupted_chunks, self.wrong_located_chunks, self.entities_prob, self.shared_offset, self.count_chunks() 

    def get_path(self):
        """ Returns the path of the region file. """
        return self.path

    def count_chunks(self, problem = None):
        """ Counts chunks in the region file with the given problem.
            If problem is omited or None, counts all the chunks. Returns
            an integer with the counter. """
        counter = 0
        for coords in self.keys():
            if self[coords] and (self[coords][TUPLE_STATUS] == problem or problem == None):
                counter += 1

        return counter

    def get_global_chunk_coords(self, chunkX, chunkZ):
        """ Takes the region filename and the chunk local
            coords and returns the global chunkcoords as integerss """

        regionX, regionZ = self.get_coords()
        chunkX += regionX*32
        chunkZ += regionZ*32

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
            coordX = int(l[1])
            coordZ = int(l[2])

            return coordX, coordZ

    def list_chunks(self, status = None):
        """ Returns a list of all the ScannedChunk objects of the chunks
            with the given status, if no status is omited or None,
            returns all the existent chunks in the region file """

        l = []
        for c in self.keys():
            t = self[c]
            if status == t[TUPLE_STATUS]:
                l.append((self.get_global_chunk_coords(*c),t))
            elif status == None:
                l.append((self.get_global_chunk_coords(*c),t))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks. The summary
            is a string with region file, global coords, local coords,
            and status of every problematic chunk. """
        text = ""
        if self.status == REGION_TOO_SMALL:
            text += " |- This region file is too small in size to actually be a region file.\n"
        else:
            for c in self.keys():
                if self[c][TUPLE_STATUS] == CHUNK_OK or self[c][TUPLE_STATUS] == CHUNK_NOT_CREATED: continue
                status = self[c][TUPLE_STATUS]
                h_coords = c
                g_coords = self.get_global_chunk_coords(*h_coords)
                text += " |-+-Chunk coords: header {0}, global {1}.\n".format(h_coords, g_coords)
                text += " | +-Status: {0}\n".format(CHUNK_STATUS_TEXT[status])
                if self[c][TUPLE_STATUS] == CHUNK_TOO_MANY_ENTITIES:
                    text += " | +-Nº entities: {0}\n".format(self[c][TUPLE_NUM_ENTITIES])
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

    def remove_entities(self):
        """ Removes all the entities in chunks with the problematic
            status CHUNK_TOO_MANY_ENTITIES that are in this region file.
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
        for c in self.keys():
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


class RegionSet(object):
    """Stores an arbitrary number of region files and the scan results.
        Inits with a list of region files. The regions dict is filled
        while scanning with ScannedRegionFiles and ScannedChunks."""
    def __init__(self, regionset_path = None, region_list = []):
        if regionset_path:
            self.path = regionset_path
            self.region_list = glob(join(self.path, "r.*.*.mca"))
        else:
            self.path = None
            self.region_list = region_list
        self.regions = {}
        for path in self.region_list:
            r = ScannedRegionFile(path)
            self.regions[r.get_coords()] = r
        self.corrupted_chunks = 0
        self.wrong_located_chunks = 0
        self.entities_problems = 0
        self.shared_header = 0
        self.bad_list = []
        self.scanned = False

    def get_name(self):
        """ Return a string with the name of the dimension, the
        directory if there is no name or "" if there's nothing """

        dim_directory = self._get_dimension_directory()
        if dim_directory:
            try: return DIMENSION_NAMES[dim_directory]
            except: return dim_directory
        else:
            return ""

    def _get_dimension_directory(self):
        """ Returns a string with the directory of the dimension, None
        if there is no such a directory and the regionset is composed
        of sparse region files. """
        if self.path:
            rest, region = split(self.path)
            rest, dim_path = split(rest)
            if dim_path == "": dim_path = split(rest)[1]
            return dim_path

        else: return None

    def __str__(self):
        text = "Region-set information:\n"
        if self.path:
            text += "   Regionset path: {0}\n".format(self.path)
        text += "   Region files: {0}\n".format(len(self.regions))
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    def __getitem__(self, key):
        return self.regions[key]

    def __setitem__(self, key, value):
        self.regions[key] = value

    def __delitem__(self, key):
        del self.regions[key]

    def __len__(self):
        return len(self.regions)

    def keys(self):
        return self.regions.keys()

    def list_regions(self, status = None):
        """ Returns a list of all the ScannedRegionFile objects stored
            in the RegionSet with status. If status = None it returns
            all the objects."""

        if status == None:
            #~ print "Estamos tras pasar el if para status None"
            #~ print "Los valores de el dict son:"
            #~ print self.regions.values()
            #~ print "El diccionario es si es:"
            #~ print self.regions
            return self.regions.values()
        t = []
        for coords in self.regions.keys():
            r = self.regions[coords]
            if r.status == status:
                t.append(r)
        return t

    def count_regions(self, status = None):
        """ Return the number of region files with status. If none
            returns the number of region files in this regionset.
            Possible status are: empty, too_small """

        counter = 0
        for r in self.keys():
            if status == self[r].status: counter += 1
            elif status == None: counter += 1
        return counter

    def count_chunks(self, problem = None):
        """ Returns the number of chunks with the given problem. If
            problem is None returns the number of chunks. """
        counter = 0
        for r in self.keys():
            counter += self[r].count_chunks(problem)
        return counter

    def list_chunks(self, status = None):
        """ Returns a list of the ScannedChunk objects of the chunks
            with the given status. If status = None returns all the
            chunks. """
        l = []
        for r in self.keys():
            l.extend(self[r].list_chunks(status))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks in this 
            regionset. The summary is a string with global coords,
            local coords, data coords and status. """
        text = ""
        for r in self.keys():
            if not (self[r].count_chunks(CHUNK_CORRUPTED) or self[r].count_chunks(CHUNK_TOO_MANY_ENTITIES) or self[r].count_chunks(CHUNK_WRONG_LOCATED) or self[r].count_chunks(CHUNK_SHARED_OFFSET) or self[r].status == REGION_TOO_SMALL):
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
            print ' Deleting chunks in region set \"{0}\":'.format(self._get_dimension_directory())
            for r in self.regions.keys():
                counter += self.regions[r].remove_problematic_chunks(problem)
            print "Removed {0} chunks in this regionset.\n".format(counter)

        return counter

    def remove_entities(self):
        """ Removes entities in chunks with the status
            TOO_MANY_ENTITIES. """
        counter = 0
        for r in self.regions.keys():
            counter += self.regions[r].remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the regionset when
            the option entity limit is changed. """
        for r in self.keys():
            self[r].rescan_entities(options)

    def generate_report(self, standalone):
        """ Generates a report of the last scan. If standalone is True
        it will generate a report to print in a terminal. If it's False
        it will returns the counters of every problem. """

        # collect data
        corrupted = self.count_chunks(CHUNK_CORRUPTED)
        wrong_located = self.count_chunks(CHUNK_WRONG_LOCATED)
        entities_prob = self.count_chunks(CHUNK_TOO_MANY_ENTITIES)
        shared_prob = self.count_chunks(CHUNK_SHARED_OFFSET)
        total_chunks = self.count_chunks()

        too_small_region = self.count_regions(REGION_TOO_SMALL)
        unreadable_region = self.count_regions(REGION_UNREADABLE)
        total_regions = self.count_regions()
        
        if standalone:
            text = ""
        
            # Print all this info in a table format
            # chunks
            chunk_errors = ("Problem","Corrupted","Wrong l.","Etities","Shared o.", "Total chunks")
            chunk_counters = ("Counts",corrupted, wrong_located, entities_prob, shared_prob, total_chunks)
            table_data = []
            for i, j in zip(chunk_errors, chunk_counters):
                table_data.append([i,j])
            text += "\nChunk problems:"
            if corrupted or wrong_located or entities_prob or shared_prob:
                text += table(table_data)
            else:
                text += "\nNo problems found.\n"

            # regions
            text += "\n\nRegion problems:\n"
            region_errors = ("Problem","Too small","Unreadable","Total regions")
            region_counters = ("Counts", too_small_region,unreadable_region, total_regions)
            table_data = []
            # compose the columns for the table
            for i, j in zip(region_errors, region_counters):
                table_data.append([i,j])
            if too_small_region:
                text += table(table_data)
            else:
                text += "No problems found."
                
            return text
        else:
            return corrupted, wrong_located, entities_prob, shared_prob, total_chunks, too_small_region, unreadable_region, total_regions

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
        # let's scan level.dat here so we can extract the world name
        # right now
        level_dat_path = join(self.path, "level.dat")
        if exists(level_dat_path):
            try:
                self.level_data = nbt.NBTFile(level_dat_path)["Data"]
                self.name = self.level_data["LevelName"].value
                self.scanned_level = ScannedDatFile(level_dat_path, readable = True, status_text = "OK")
            except Exception, e:
                self.name = None
                self.scanned_level = ScannedDatFile(level_dat_path, readable = False, status_text = e)
        else:
            self.level_file = None
            self.level_data = None
            self.name = None
            self.scanned_level = ScannedDatFile(None, False, "The file doesn't exist")

        # player files
        player_paths = glob(join(join(self.path, "players"), "*.dat"))
        self.players = {}
        for path in player_paths:
            name = split(path)[1].split(".")[0]
            self.players[name] = ScannedDatFile(path)

        # does it look like a world folder?
        region_files = False
        for region_directory in self.regionsets:
            if region_directory:
                region_files = True
        if region_files:
            self.isworld = True
        else:
            self.isworld = False

        # set in scan.py, used in interactive.py
        self.scanned = False

    def __str__(self):
        text = "World information:\n"
        text += "   World path: {0}\n".format(self.path)
        text += "   World name: {0}\n".format(self.name)
        text += "   Region files: {0}\n".format(self.get_number_regions())
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

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

        # dat files info
        final += "\nlevel.dat:\n"
        if self.scanned_level.readable:
            final += "\t\'level.dat\' is readable\n"
        else:
            final += "\t[WARNING]: \'level.dat\' isn't readable, error: {0}\n".format(self.scanned_level.status_text)

        all_ok = True
        final += "\nPlayer files:\n"
        for name in self.players:
            if not self.players[name].readable:
                all_ok = False
                final += "\t-[WARNING]: Player file {0} has problems.\n\t\tError: {1}\n\n".format(self.players[name].filename, self.players[name].status_text)
        if all_ok:
            final += "\tAll player files are readable.\n\n"

        # chunk info
        chunk_info = ""
        for regionset in self.regionsets:
            
            title = regionset.get_name()
            
            # don't add text if there aren't broken chunks
            text = regionset.summary()
            chunk_info += (title + text) if text else ""
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

    def replace_problematic_chunks(self, backup_worlds, problem, options):
        """ Takes a list of world objects and a problem value and try
            to replace every chunk with that problem using a working
            chunk from the list of world objects. It uses the world
            objects in left to riht order. """

        counter = 0
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
                    print "The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dimension_directory())
                else:
                    for c in bad_chunks:
                        global_coords = c[0]
                        status_tuple = c[1]
                        local_coords = _get_local_chunk_coords(*global_coords)
                        print "\n{0:-^60}".format(' New chunk to replace. Coords: x = {0}; z = {1} '.format(*global_coords))

                        # search for the region file
                        backup_region_path, local_coords = b_regionset.locate_chunk(global_coords)
                        tofix_region_path, _ = regionset.locate_chunk(global_coords)
                        if exists(backup_region_path):
                            print "Backup region file found in:\n  {0}".format(backup_region_path)
                            
                            # scan the whole region file, pretty slow, but completely needed to detec sharing offset chunks
                            from scan import scan_region_file
                            r = scan_region_file(ScannedRegionFile(backup_region_path),options)
                            try:
                                status_tuple = r[local_coords]
                            except KeyError:
                                status_tuple = None
                            
                            # retrive the status from status_tuple
                            if status_tuple == None:
                                status = CHUNK_NOT_CREATED
                            else:
                                status = status_tuple[TUPLE_STATUS]
                            
                            if status == CHUNK_OK:
                                backup_region_file = region.RegionFile(backup_region_path)
                                working_chunk = backup_region_file.get_chunk(local_coords[0],local_coords[1])

                                print "Replacing..."
                                # the chunk exists and is healthy, fix it!
                                tofix_region_file = region.RegionFile(tofix_region_path)
                                # first unlink the chunk, second write the chunk.
                                # unlinking the chunk is more secure and the only way to replace chunks with 
                                # a shared offset withou overwriting the good chunk
                                tofix_region_file.unlink_chunk(*local_coords)
                                tofix_region_file.write_chunk(local_coords[0], local_coords[1],working_chunk)
                                counter += 1
                                print "Chunk replaced using backup dir: {0}".format(backup.path)

                            else:
                                print "Can't use this backup directory, the chunk has the status: {0}".format(CHUNK_STATUS_TEXT[status])
                                continue

                        else:
                            print "The region file doesn't exist in the backup directory: {0}".format(backup_region_path)

        return counter


    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_chunks(problem)
        return counter

    def replace_problematic_regions(self, backup_worlds, problem, options):
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
                    print "The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dimension_directory())
                else:
                    for r in bad_regions:
                        print "\n{0:-^60}".format(' New region file to replace! Coords {0} '.format(r.get_coords()))

                        # search for the region file
                        
                        try:
                            backup_region_path = b_regionset[r.get_coords()].get_path()
                        except:
                            backup_region_path = None
                        tofix_region_path = r.get_path()
                        
                        if backup_region_path != None and exists(backup_region_path):
                            print "Backup region file found in:\n  {0}".format(backup_region_path)
                            # check the region file, just open it.
                            try:
                                backup_region_file = region.RegionFile(backup_region_path)
                            except region.NoRegionHeader as e:
                                print "Can't use this backup directory, the error while opening the region file: {0}".format(e)
                                continue
                            except Exception as e:
                                print "Can't use this backup directory, unknown error: {0}".format(e)
                                continue
                            copy(backup_region_path, tofix_region_path)
                            print "Region file replaced!"
                            counter += 1
                        else:
                            print "The region file doesn't exist in the backup directory: {0}".format(backup_region_path)

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
        
        # collect data
        corrupted = self.count_chunks(CHUNK_CORRUPTED)
        wrong_located = self.count_chunks(CHUNK_WRONG_LOCATED)
        entities_prob = self.count_chunks(CHUNK_TOO_MANY_ENTITIES)
        shared_prob = self.count_chunks(CHUNK_SHARED_OFFSET)
        total_chunks = self.count_chunks()

        too_small_region = self.count_regions(REGION_TOO_SMALL)
        unreadable_region = self.count_regions(REGION_UNREADABLE)
        total_regions = self.count_regions()
        
        if standalone:
            text = ""
        
            # Print all this info in a table format
            chunk_errors = ("Problem","Corrupted","Wrong l.","Etities","Shared o.", "Total chunks")
            chunk_counters = ("Counts",corrupted, wrong_located, entities_prob, shared_prob, total_chunks)
            table_data = []
            for i, j in zip(chunk_errors, chunk_counters):
                table_data.append([i,j])
            text += "\nChunk problems:\n"
            if corrupted or wrong_located or entities_prob or shared_prob:
                text += table(table_data)
            else:
                text += "No problems found.\n"

            text += "\n\nRegion problems:\n"
            region_errors = ("Problem","Too small","Unreadable","Total regions")
            region_counters = ("Counts", too_small_region,unreadable_region, total_regions)
            table_data = []
            # compose the columns for the table
            for i, j in zip(region_errors, region_counters):
                table_data.append([i,j])
            if too_small_region:
                text += table(table_data)
            else:
                text += "No problems found."
                
            return text
        else:
            return corrupted, wrong_located, entities_prob, shared_prob, total_chunks, too_small_region, unreadable_region, total_regions



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

    regionX = chunkX / 32
    regionZ = chunkZ / 32

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

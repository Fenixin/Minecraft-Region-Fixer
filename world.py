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
from glob import glob
from os.path import join, split, exists

import time

# Constants. Used to mark the status of a chunks:
CHUNK_NOT_CREATED = -1
CHUNK_OK = 0
CHUNK_CORRUPTED = 1
CHUNK_WRONG_LOCATED = 2
CHUNK_TOO_MUCH_ENTITIES = 3


class ScannedChunk(object):
    def __init__(self, header_coords, global_coords = None, data_coords = None, status = None, num_entities = None, scan_time = None):
        # no sé si debería poner más información en este obj
        self.h_coords = header_coords
        self.g_coords = global_coords
        self.d_coords = data_coords
        self.status = status
        self.status_text = None
        self.num_entities = num_entities
        self.scan_time = scan_time
    def __repr__(self):
        # TODO esto corresponde a __str__ !
        text = "Chunk with header coordinates:" + str(self.h_coords) + "\n"
        text += "\tData coordinates:" + str(self.d_coords) + "\n"
        text +="\tGlobal coordinates:" + str(self.g_coords) + "\n"
        text += "\tStatus:" + str(self.status_text) + "\n"
        text += "\tNumber of entities:" + str(self.num_entities) + "\n"
        text += "\tScan time:" + time.ctime(self.scan_time) + "\n"
        return text

class ScannedRegionFile(object):
    """ Stores all the info for a scanned region file """
    def __init__(self, filename, corrupted = None, wrong = None, entities_prob = None, chunks = None, time = None):
        self.path = filename
        self.filename = split(filename)[1]
        self.folder = split(filename)[0]
        self.x, self.z = get_region_coords(filename)
        self.coords = (self.x, self.z)

        # en el caso de wrong located podría almacenar la dirección real
        # donde se encuentra y donde dice que está los datos almacenados
        self.chunks = {}
        
        # quizás estos deberían ser contadores
        self.corrupted_chunks = corrupted
        self.wrong_located_chunks = wrong
        self.entities_prob = entities_prob
        self.chunk_count = chunks
        
        # time when the scan finished
        self.last_scan_time = time

    def count_problems(self, problem):
        counter = 0
        for chunk in self.chunks.keys():
            if self.chunks[chunk].status == problem:
                counter += 1
        return counter

    def count_chunks(self):
        counter = 0
        for chunk in self.chunks.keys():
            if self.chunks[chunk].status != CHUNK_NOT_CREATED:
                counter += 1
        return counter

class RegionSet(object):
    """Stores an arbitrary number of region files and the scan results
    Inits with a list of region files and the regions dict is filled
    while scanning with ScannedRegionFiles and ScannedChunks."""
    def __init__(self, region_list):
        self.regions = {}
        for path in region_list:
            r = ScannedRegionFile(path)
            self.regions[(r.x, r.z)] = r
        
        self.corrupted_chunks = 0
        self.wrong_located_chunks = 0
        self.entities_problems = 0
        self.bad_list = None

    def __getitem__(self, key):
        return self.regions[key]

    def __setitem__(self, key, value):
        """ Items are ScannedRegionFile objects """
        if value.corrupted_chunks or value.wrong_located_chunks or value.entities_prob:
            self.bad_list.append(key)
            # seguramente es MUCHO mejor contar los valores cada vez que haga falta
            # que no tiene que ser tan lento. mantenerlos en sincronía es
            # seguramente muy mala idea
            if value.corrupted_chunks:
                self.corrupted_chunks += value.corrupted_chunks
            if value.corrupted_chunks:
                self.wrong_located_chunks += value.wrong_located_chunks
            if value.entities_prob:
                self.entities_problems += value.entities_prob
        self.regions[key] = value
    
    def __delitem__(self, key):
        # TODO this may raise ValueError, left it in here to test this
        if value.corrupted_chunks or value.wrong_located_chunks or value.entities_prob:
            bad_list.remove(key)
            if value.corrupted_chunks:
                self.corrupted_chunks -= value.corrupted_chunks
            if value.corrupted_chunks:
                self.wrong_located_chunks -= value.wrong_located_chunks
            if value.entities_prob:
                self.entities_problems -= value.entities_prob

        del self.regions[key]
    
    def __len__(self):
        return len(self.regions)

    def keys(self):
        return self.regions.keys()
    
    def get_region_list(self):
        t = []
        for e in self.regions.keys():
            t.append(self.regions[e])
        return t
    
    def count_problems(self, problem):
        counter = 0
        for r in self.keys():
            counter += self[r].count_problems(problem)
        return counter
    
    def count_chunks(self):
        counter = 0
        for r in self.keys():
            counter += self[r].count_chunks()
        return counter

class World(object):
    """ This class stores all the info needed of a world, and once
    scanned, stores all the problems found. It also has all the tools
    needed to modify the world."""
    
    def __init__(self, world_path):
        self.world_path = world_path
        
        # variables for region files
        self.normal_region_files = RegionSet(glob(join(self.world_path, "region/r.*.*.mca")))
        self.nether_region_files = RegionSet(glob(join(self.world_path,"DIM-1/region/r.*.*.mca")))
        self.aether_region_files = RegionSet(glob(join(self.world_path,"DIM1/region/r.*.*.mca")))
        #~ self.all_region_files = self.normal_region_files + self.nether_region_files + self.aether_region_files
        self.num_chunks = None # not used right now
        # dict storing all the problems found in the region files
        #~ self.region_problems = {}
        
        # for level.dat
        self.level_file = join(self.world_path, "level.dat")
        if exists(self.level_file):
            self.level_data = nbt.NBTFile(self.level_file)["Data"]
            self.name = self.level_data["LevelName"]
        else:
            self.level_file = None
            self.level_data = None
            self.name = None
        # dictionary used to store all the problems found in level.dat file
        self.level_problems = []
        
        # for player files
        # not sure yet how to store this properly because I'm not sure
        # on what to scan about players.
        self.player_files = glob(join(join(self.world_path, "players"), "*.dat"))
        self.player_with_problems = []
        self.player_status = {}

        # does it look like a world folder?
        if self.normal_region_files.regions or self.nether_region_files.regions \
        or self.aether_region_files.regions or self.level_file or self.player_files:
            self.isworld = True
        else:
            self.isworld = False
    
    def get_name(self):
        """ Returns a string with the name as found in level.dat or
            with the world folder's name. """
        if self.name:
            return self.name
        else:
            return split(self.world_path)[-1]

    def count_problems(self, problem):
        """ Counts problems  """

        counter = self.normal_region_files.count_problems(problem) + self.nether_region_files.count_problems(problem) + self.aether_region_files.count_problems(problem)

        return counter

    def count_chunks(self):
        """ Counts problems  """

        counter = self.normal_region_files.count_chunks() + self.nether_region_files.count_chunks() + self.aether_region_files.count_chunks()

        return counter

    def replace_problematic_chunks(self, backup_worlds, problem):
        """ Takes a list of world objects and a problem value and try
            to replace every chunk with that problem using a working
            chunk from the list of world objects. It uses the world
            objects in left to riht order. """

        counter = 0
        # this list is used to remove chunks from the problems
        # dict once the iteration over it has finished, doing it at the 
        # same time is not a good idea
        fixed_chunks = []

        for mcr_path in self.mcr_problems:
            for chunk in self.mcr_problems[mcr_path]:

                if problem in self.mcr_problems[mcr_path][chunk]:
                    print "\n{0:-^60}".format(' New chunk to fix! ')
                    for backup in backup_worlds:

                        # search for the region file
                        region_name = split(mcr_path)[1]
                        dimension = split(split(mcr_path)[0])[1]
                        if dimension == "region":
                            backup_region_path = join(backup.world_path, "region", region_name)
                        else:
                            backup_region_path = join(backup.world_path, dimension, region_name)

                        if exists(backup_region_path):
                            print "Backup region file found in: {0} \nfixing...".format(backup_region_path)

                            # get the chunk
                            from scan import scan_chunk
                            backup_region_file = region.RegionFile(backup_mcr_path)
                            working_chunk, status, errmsg = scan_chunk(backup_region_file, chunk[0], chunk[1])
                            del backup_region_file

                            ####### TODO TODO TODO
                            # would be cool to check here for entities problem?

                            if isinstance(working_chunk, nbt.TAG_Compound):
                                # the chunk exists and is non-corrupted, fix it!
                                tofix_region_file = region.RegionFile(mcr_path)
                                tofix_region_file.write_chunk(chunk[0], chunk[1],working_chunk)
                                del tofix_region_file
                                counter += 1
                                fixed_chunks.append((mcr_path, chunk, problem))
                                print "Chunk fixed using backup dir: {0}".format(backup.world_path)
                                break

                            elif working_chunk == None:
                                print "The chunk doesn't exists in this backup directory: {0}".format(backup.world_path)
                                # The chunk doesn't exists in the region file
                                continue

                            elif status == -1:
                                # The chunk is corrupted
                                print "The chunk is corrupted in this backup directory: {0}".format(backup.world_path)
                                continue

                            elif status == -2:
                                # The chunk is wrong located
                                print "The chunk is wrong located in this backup directory: {0}".format(backup.world_path)
                                continue

        for mcr, chunk, problem in fixed_chunks:
            self.remove_problem(mcr, chunk, problem)

        return counter


    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, it also
        removes the entry in the dictionary mcr_problems """

        deleted = []
        for reg in self.mcr_problems:
            for chunk in self.mcr_problems[reg]:
                for p in self.mcr_problems[reg][chunk]:
                    if p == problem:
                        region_file = region.RegionFile(reg)
                        region_file.unlink_chunk(chunk[0], chunk[1])
                        deleted.append((reg, chunk, "all"))
                        del region_file

        for d in deleted:
            reg, chunk, prob = d
            self.remove_problem(reg, chunk, prob)

        return len(deleted)


    def remove_problem(self, rgn, chunk, problem):
        """ Removes a problem from the mcr_problems dict for the given
            chunk. You can pass all to remove all the problem, useful
            in case the chunk has been deleted"""

        if problem == "all":
            del self.mcr_problems[rgn][chunk]
            if self.mcr_problems[rgn] == {}:
                del self.mcr_problems[rgn]
        else:
            self.mcr_problems[rgn][chunk].remove(problem)
            if self.mcr_problems[rgn][chunk] == []:
                del self.mcr_problems[rgn][chunk]
                if self.mcr_problems[rgn] == {}:
                    del self.mcr_problems[rgn]


    def delete_chunk_list(self,l):
        """ Deletes the given chunk list from the world. 
            Takes a list of tuples storing:
            (full_region_path, chunk_x, chunk_z)
            
            And returns the amount of deleted chunks.
            
            It pritns info in the process."""

        counter = 0
        for region_path, x, z in l:

            region_file = region.RegionFile(region_path)

            if region_file.header[(x,z)][3] == region_file.STATUS_CHUNK_OK:
                region_file.unlink_chunk(x, z)
                counter += 1
            else:
                print "The chunk ({0},{1}) in the region file {2} doesn't exist.".format(x, z, region_path)
            del region_file

        return counter

def get_global_chunk_coords(region_filename, chunkX, chunkZ):
    """ Takes the region filename and the chunk local 
        coords and returns the global chunkcoords as integerss """
    
    regionX, regionZ = get_region_coords(region_filename)
    chunkX += regionX*32
    chunkZ += regionZ*32
    
    return chunkX, chunkZ

def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk
        coords """
    
    regionX = chunkX / 32
    regionZ = chunkZ / 32
    
    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mcr'
    
    return region_name
    

def get_region_coords(region_filename):
    """ Splits the region filename (full pathname or just filename)
        and returns his region X and Z coordinates as integers. """

    splited = split(region_filename)
    filename = splited[1]
    l = filename.split('.')
    coordX = l[1]
    coordZ = l[2]

    return int(coordX), int(coordZ)


def get_chunk_data_coords(nbt_file):
    """ Gets the coords stored in the NBT structure of the chunk.

        Takes an nbt obj and returns the coords as integers.
        Don't confuse with get_global_chunk_coords! """

    level = nbt_file.__getitem__('Level')

    coordX = level.__getitem__('xPos').value
    coordZ = level.__getitem__('zPos').value

    return coordX, coordZ

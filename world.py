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
        # TODO no sé si debería poner más información en este obj
        self.h_coords = header_coords
        self.g_coords = global_coords
        self.d_coords = data_coords
        self.status = status
        self.status_text = None
        self.num_entities = num_entities
        self.scan_time = scan_time
    def __str__(self):
        # TODO esto corresponde a __str__ ! También ponerlo más mono
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

    def __str__(self):
        text = "Path: {0}".format(self.path)
        scanned = False
        if time:
            scanned = True
        text += "\nScanned: {0}".format(scanned)
        
        return text

    def count_chunks(self, problem = None):
        """ Counts chunks in the region file with the given problem.
            If problem is not given counts all the chunks. Returns
            an integer with the counter. """
        counter = 0
        for chunk in self.chunks.keys():
            if self.chunks[chunk].status == problem or problem == None:
                counter += 1
        return counter

    def list_chunks(self, status = None):
        """ Returns a list of all global coordinates of the chunks with
            the given status, if no status is given, returns all the
            existent chunks in the region file """
        
        l = []
        for c in self.chunks.keys():
            if status == self.chunks[c].status: l.append(self.chunks[c].g_coords)
            elif status == None: l.append(c.g_coords)
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks. The summary
            is a string with region file, global coords, local coords,
            data coords and status of every problematic chunk. """
        text = ""
        for c in self.chunks.keys():
            if self.chunks[c].status == CHUNK_OK or self.chunks[c].status == CHUNK_NOT_CREATED: continue
            status = self.chunks[c].status
            g_coords = self.chunks[c].g_coords
            h_coords = self.chunks[c].h_coords
            d_coords = self.chunks[c].d_coords
            text += " |-+-" + "Chunk coords: {0}, global {1}, data {2}. Status:\n".format(h_coords,g_coords,d_coords if d_coords != None else "N/A")
            text += " | +-" + "{0}\n".format(self.chunks[c].status_text)
            text += " |\n"
        
        return text
            
    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a 
            counter with the number of deleted chunks. """

        counter = 0
        bad_chunks = self.list_chunks(problem)
        for global_coords in bad_chunks:
            local_coords = get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            region_file.unlink_chunk(*local_coords)
            counter += 1
        
        return counter
    
    def remove_entities(self):
        problem = world.CHUNK_TOO_MUCH_ENTITIES
        counter = 0
        bad_chunks = self.list_chunks(problem)
        for global_coords in bad_chunks:
            local_coords = get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            counter += delete_entities(region_file, *local_coords)
        
        return counter


class RegionSet(object):
    """Stores an arbitrary number of region files and the scan results.
    Inits with a list of region files and the regions dict is filled
    while scanning with ScannedRegionFiles and ScannedChunks."""
    def __init__(self, regionset_path = None, region_list = []):
        # note: this self.path is not used anywhere for the moment
        if regionset_path:
            self.path = regionset_path
            self.region_list = glob(join(self.path, "r.*.*.mca"))
        else:
            self.path = None
            self.region_list = region_list
        self.regions = {}
        for path in self.region_list:
            r = ScannedRegionFile(path)
            self.regions[(r.x, r.z)] = r
        self.corrupted_chunks = 0
        self.wrong_located_chunks = 0
        self.entities_problems = 0
        self.bad_list = []
        self.scanned = False

    def __str__(self):
        text = "Region-set information:\n"
        if self.path:
            text += "   Regionset path: {0}\n".format(self.world_path)
        text += "   Region files: {0}\n".format(len(self.regions))
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

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
    
    def count_chunks(self, problem = None):
        counter = 0
        for r in self.keys():
            counter += self[r].count_chunks(problem)
        return counter

    def list_chunks(self, status = None):
        """ Returns a list of the global coordinates of the chunks
            with status. If status = None returns all the chunks. """
        l = []
        for r in self.keys():
            l.extend(self[r].list_chunks(status))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks. The summary
            is a string with global coords, local coords, data coords
            and status. """
        text = ""
        for r in self.keys():
            if not (self[r].count_chunks(CHUNK_CORRUPTED) or self[r].count_chunks(CHUNK_TOO_MUCH_ENTITIES) or self[r].count_chunks(CHUNK_WRONG_LOCATED)):
                continue
            text += "Region file: " + self[r].filename + "\n"
            text += self[r].summary()
            text += " +\n\n"
        return text

    def locate_chunk(self, global_coords):
        """ Takes the global coordinates of a chunk and returns the
            region filename and the local coordinates of the chunk or
            None, None if it doesn't exits in this RegionSet """
        
        filename = self.path + get_chunk_region(*global_coords)
        local_coords = get_local_chunk_coords(*global_coords)
        
        return filename, local_coords
    
    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a 
            counter with the number of deleted chunks. """

        counter = 0
        print ' Deleting chunks in region set \"{0}\":'.format(self.path),
        for r in self.regions.keys():
            counter += self.regions[r].remove_problematic_chunks(problem)
        print "Done! Removed {0} chunks".format(counter)
        return counter
    
    def remove_entities(self):
        counter = 0
        problem = CHUNK_TOO_MUCH_ENTITIES
        for r in self.regions.keys():
            counter += self.regions[r].remove_problematic_chunks(problem)
        return counter


class World(object):
    """ This class stores all the info needed of a world, and once
    scanned, stores all the problems found. It also has all the tools
    needed to modify the world."""
    
    def __init__(self, world_path):
        self.world_path = world_path
        
        # variables for region files
        self.normal_region_files = RegionSet(join(self.world_path, "region/"))
        self.nether_region_files = RegionSet(join(self.world_path,"DIM-1/region/"))
        self.aether_region_files = RegionSet(join(self.world_path,"DIM1/region/"))
        #~ self.all_region_files = self.normal_region_files + self.nether_region_files + self.aether_region_files
        self.num_chunks = None # not used right now
        # dict storing all the problems found in the region files
        #~ self.region_problems = {}
        
        # for level.dat
        self.level_file = join(self.world_path, "level.dat")
        if exists(self.level_file):
            self.level_data = nbt.NBTFile(self.level_file)["Data"]
            self.name = self.level_data["LevelName"].value
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
        
        # set in scan.py, used in interactive.py
        self.scanned = False
        
    def __str__(self):
        text = "World information:\n"
        text += "   World path: {0}\n".format(self.world_path)
        text += "   World name: {0}\n".format(self.name)
        text += "   Region files: {0}\n".format(len(self.normal_region_files) + len(self.nether_region_files) + len(self.aether_region_files))
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    def summary(self):
        final = ""
        for dimension in ["overworld", "nether", "end"]:
            
            if dimension == "overworld":
                regionset = self.normal_region_files
                title = "Overworld:\n"
            elif dimension == "nether":
                regionset = self.nether_region_files
                title =  "Nether:\n"
            elif dimension == "end":
                regionset = self.aether_region_files
                title = "End:\n"

            # don't add text if there aren't broken chunks
            text = regionset.summary()
            final += (title + text) if text else ""

        return final

    def get_name(self):
        """ Returns a string with the name as found in level.dat or
            with the world folder's name. """
        if self.name:
            return self.name
        else:
            return split(self.world_path)[-1]

    def count_chunks(self, problem = None):
        """ Counts problems  """

        counter = self.normal_region_files.count_chunks(problem) + self.nether_region_files.count_chunks(problem) + self.aether_region_files.count_chunks(problem)

        return counter

    def list_chunks(self, status):
        """ Returns a list of the global coordinates of chunks with
            status. WARNING: this don't make any difference between dimensions
            use RegionSet.list_chunks instead"""
        # TODO does this have any problems with the different dimensions?
        # where is this used? When replacing chunks regionset.list_chunks is used
        # there shouldn't be any problems
        # TODO this isn't used anywhere
        return self.normal_region_files.list_chunks(status) + self.nether_region_files.list_chunks(status) + self.aether_region_files.list_chunks(status)

    def replace_problematic_chunks(self, backup_worlds, problem, options):
        """ Takes a list of world objects and a problem value and try
            to replace every chunk with that problem using a working
            chunk from the list of world objects. It uses the world
            objects in left to riht order. """

        counter = 0
        # this list is used to remove chunks from the problems
        # dict once the iteration over it has finished, doing it at the 
        # same time is not a good idea
        fixed_chunks = []
        
        # TODO TODO TODO esto parece tener algunos problemas serios,
        # aunque tb parece que funciona....

        for dimension in ["overworld", "nether", "end"]:
            for backup in backup_worlds:
                # choose the correct regionset
                if dimension == "overworld":
                    regionset = self.normal_region_files
                    b_regionset = backup.normal_region_files
                elif dimension == "nether":
                    regionset = self.nether_region_files
                    b_regionset = backup.nether_region_files
                elif dimension == "end":
                    regionset = self.aether_region_files
                    b_regionset = backup.aether_region_files
                
                bad_chunks = regionset.list_chunks(problem)
                for global_coords in bad_chunks:
                    print "\n{0:-^60}".format(' New chunk to replace! Coords {0} '.format(global_coords))

                    # search for the region file
                    backup_region_path, local_coords = b_regionset.locate_chunk(global_coords)
                    tofix_region_path, _ = regionset.locate_chunk(global_coords)
                    if exists(backup_region_path):
                        print "Backup region file found in: {0}".format(backup_region_path)

                        # get the chunk
                        from scan import scan_chunk
                        backup_region_file = region.RegionFile(backup_region_path)
                        working_chunk, region_file, coords, data_coords, global_coords, num_entities, status, status_text, scan_time = \
                            scan_chunk(backup_region_file, local_coords, options)
                        
                        print working_chunk, region_file, coords, data_coords, global_coords, num_entities, status, status_text, scan_time

                        if status == CHUNK_OK:
                            print "Replacing..."
                            # the chunk exists and is non-corrupted, fix it!
                            tofix_region_file = region.RegionFile(tofix_region_path)
                            tofix_region_file.write_chunk(local_coords[0], local_coords[1],working_chunk)
                            counter += 1
                            fixed_chunks.append((tofix_region_path, local_coords, status))
                            print "Chunk replaced using backup dir: {0}".format(backup.world_path)

                        elif status == CHUNK_NOT_CREATED:
                            print "The chunk doesn't exists in this backup directory: {0}".format(backup.world_path)
                            continue

                        elif status == CHUNK_CORRUPTED:
                            print "The chunk is corrupted in this backup directory: {0}".format(backup.world_path)
                            continue

                        elif status == CHUNK_WRONG_LOCATED:
                            print "The chunk is wrong located in this backup directory: {0}".format(backup.world_path)
                            continue
                        
                        elif status == CHUNK_TOO_MUCH_ENTITIES:
                            print "The chunk in this backup directory has too many entities ({1} entities): {0}".format(backup.world_path, num_entities)
                            continue

                    else:
                        print "The region file doesn't exist in the backup directory: {0}".format(backup_region_path)

        return counter


    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, it also
        removes the entry in the dictionary mcr_problems """

        counter = 0
        for dimension in ["overworld", "nether", "end"]:
            if dimension == "overworld":
                regionset = self.normal_region_files
            elif dimension == "nether":
                regionset = self.nether_region_files
            elif dimension == "end":
                regionset = self.aether_region_files

            counter += regionset.remove_problematic_chunks(problem)

        return counter


    def remove_problem(self, rgn, chunk, problem):
        # TODO: I think this isn't used anymore
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
        # TODO: I think this doesn't work anymore
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
    
    def remove_entities(self):
        """ Delete all the entities in the chunks that have more than
            entity-limit entities. """
        
        counter = 0
        for dimension in ["overworld", "nether", "end"]:
            if dimension == "overworld":
                regionset = self.normal_region_files
            elif dimension == "nether":
                regionset = self.nether_region_files
            elif dimension == "end":
                regionset = self.aether_region_files

            counter += regionset.remove_entities()

        return counter

    
def delete_entities(region_file, x, z):
    """ Takes the region file and the chunk coordinates. Deletes all 
        the entities in the chunk. Returns nothing. """
    # not sure where to put this function
    chunk = region_file.get_chunk(x,z)
    counter = len(chunk['Level']['Entities'])
    empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')
    chunk['Level']['Entities'] = empty_tag_list
    region_file.write_chunk(x, z, chunk)
    
    return counter

def get_global_chunk_coords(region_filename, chunkX, chunkZ):
    """ Takes the region filename and the chunk local 
        coords and returns the global chunkcoords as integerss """
    
    regionX, regionZ = get_region_coords(region_filename)
    chunkX += regionX*32
    chunkZ += regionZ*32
    
    return chunkX, chunkZ

def get_local_chunk_coords(chunkx, chunkz):
    """ Takes the chunk global coords and returns the local coords """
    return chunkx % 32, chunkz % 32

def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk
        coords """
    
    regionX = chunkX / 32
    regionZ = chunkZ / 32
    
    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mca'
    
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

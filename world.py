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
from os.path import join, split, exists, getsize

class World(object):
    """ Stores all the info needed of a world, and once scanned, stores
    all the problems found """
    
    def __init__(self, world_path):
        self.world_path = world_path
        self.normal_mcr_files = glob(join(self.world_path, "region/r.*.*.mcr"))
        self.nether_mcr_files = glob(join(self.world_path,"DIM-1/region/r.*.*.mcr"))
        self.all_mcr_files = self.normal_mcr_files + self.nether_mcr_files
        
        self.level_file = join(self.world_path, "level.dat")
        self.level_status = {}
        
        self.player_files = glob(join(join(self.world_path, "players"), "*.dat"))
        self.players_status = {}
        self.player_problems = []
        
        self.world_problems = {}
        
        # Constants
        self.CORRUPTED = 1
        self.WRONG_LOCATED = 2
        self.TOO_MUCH_ENTITIES = 3

def get_global_chunk_coords(region_filename, chunkX, chunkZ):
    """ Takes the region filename and the chunk local 
    coords and returns the global chunkcoords as integerss """
    
    regionX, regionZ = get_region_coords(region_filename)
    chunkX += regionX*32
    chunkZ += regionZ*32
    
    return chunkX, chunkZ

def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk coords """
    
    regionX = chunkX / 32
    regionZ = chunkZ / 32
    
    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mcr'
    
    return region_name
    

def get_region_coords(region_filename):
    """ Splits the region filename (full pathname or just filename)
        and returns his region coordinates.
        Return X and Z coords as integers. """
    
    splited = split(region_filename)
    filename = splited[1]
    list = filename.split('.')
    coordX = list[1]
    coordZ = list[2]
    
    return int(coordX), int(coordZ)
    
def get_chunk_data_coords(nbt_file):
    """ Gets the coords stored in the NBT structure of the chunk.
        Takes an nbt obj and returns the coords as integers.
        Don't confuse with get_global_chunk_coords! """
    
    level = nbt_file.__getitem__('Level')
            
    coordX = level.__getitem__('xPos').value
    coordZ = level.__getitem__('zPos').value
    
    return coordX, coordZ

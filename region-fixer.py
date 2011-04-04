#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
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

import argparse
from glob import glob
from os.path import join, split, exists, getsize
import nbt.region as region
import zlib
import gzip
import nbt.nbt as nbt

def parse_backup_list(world_backup_dirs):
    """ Generates a list with the input of backup dirs, also check if
    the backups dirs exists"""
    region_backup_dirs = []
    directories = world_backup_dirs.split(',')
    for dir in directories:
        region_dir = join(dir,"region")
        if exists(region_dir):
            region_backup_dirs.append(region_dir)
        else:
            print "[ATTENTION] The directory \"{0}\" is not a minecraft world directory".format(dir)
    return region_backup_dirs

def check_region_file(region_file):
    """ Takes a RegionFile obj and returns a list of corrupted 
    chunks where each element represents a corrupted chunk and
    contains a tuple:
     (region file, coord x, coord y) 
     and returns also the total number of chunks (including corrupted ones)
     """
    total_chunks = 0
    bad_chunks = []
    try:
        for x in range(32):
            for z in range(32):
                #~ print "({0},{1})".format(x,z),
                chunk = check_chunk(region_file, x, z)
                
                if isinstance(chunk, nbt.TAG_Compound):
                    total_chunks += 1
                elif chunk == -1:
                    total_chunks += 1
                    bad_chunks.append((region_file.filename,x,z))
                # if is None do nothing
                
        region_file.__del__()
        
    except KeyboardInterrupt:
        print "\nInterrupted by user\n"
        exit()
        
    return bad_chunks, total_chunks


def check_chunk(region_file, x, z):
    """ Returns the chunk if exists, -1 if it's corrupted and None if
    it doesn't exist.
    """
    try:
        chunk = region_file.get_chunk(x,z)
        
    except zlib.error:
        return -1
        
    #~ except IOError: # This one and the next are a workaround!
        #~ return -1
    
    #~ except OverflowError: # they need to be handled in nbt and region
        #~ return -1
    
    return chunk
        

def main():
    
    parser = argparse.ArgumentParser(description='Script to check the integrity of a region file, \
                                            and to fix it, when posible, using with a backup of the map. \
                                            It uses NBT by twoolie the fork by MidnightLightning. \
                                            Written by Alejandro Aguilera (Fenixin). Sponsored by \
                                            NITRADO Servers (http://nitrado.net)',\
                                            prog = 'region-fixer')
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.1')
    parser.add_argument('world', metavar = '<world>', type = str, help = 'Minecraft world directory. If it\'s called only with this \
                                            option it will scan the world and print the number of corrupted chunks ', default = None)
    parser.add_argument('--backups', metavar = '<backups>', type = str, help = 'List of backup directories of the Minecraft world. \
                                        Warning! This script is not going to check if it\'s the same world, so be careful! \
                                        This argument can be a comma separated list (but never with spaces between elements!).', default = None)
    parser.add_argument('--delete', action = 'store_true', help = '[WARNING!] This option deletes! And deleting can make you lose data, so be careful! :P \
                                            This option will delete all the corrupted chunk. Used with --backups it will delete all the non-fixed chunks. \
                                            Minecraft will regenerate the chunk. TODO at the moment this only deletes the header \
                                            leaving the chunk data in place.', default = False)
    args = parser.parse_args()

    # do things with the args
    world_backup_dirs = args.backups
    if world_backup_dirs: # create a list of directories containing the backup of the region files
        region_backup_dirs = parse_backup_list(world_backup_dirs)
        if not region_backup_dirs:
            print "[WARNING] No valid backup directories found. Will only scan the world."

    world = args.world
    world_region_dir = join(world,"region")
    print "Scanning directory..."
    region_files = glob(world_region_dir + "/r.*.*.mcr")

    print "There are {0} region files found on the world directory.".format(len(region_files))


    # check for corrupted chunks
    print 
    print "{0:#^60}".format(' Scanning for corrupted chunks ')

    total_chunks = 0
    bad_chunks = []
    total_regions = len(region_files)
    counter_region = 0
    for region_path in region_files:
        counter_region += 1
        print "Scanning {0}   ...  {1}/{2}".format(region_path, counter_region, total_regions)
        if getsize(region_path) != 0:
            region_file = region.RegionFile(region_path)
        else:
            continue
        list, chunks = check_region_file(region_file)
        
        bad_chunks.extend(list)
        total_chunks += chunks

    print "Found {0} corrupted chunks of {1}\n".format(len(bad_chunks),total_chunks)


    # Try to fix corrupted chunks with the backup copy

    if world_backup_dirs and bad_chunks:
        print "{0:#^60}".format(' Trying to fix corrupted chunks ')
        delete_chunks = bad_chunks # don't worry, fixed chunk are removed
                                   # from this list, and this will be used
                                   # in the next part
        counter_fixed = 0
        
        for corrupted_chunk in bad_chunks:
            x = corrupted_chunk[1]
            z = corrupted_chunk[2]

            print "\n{0:-^60}".format(' New chunk to fix! ')

            for backup in region_backup_dirs:
                Fixed = False
                region_file = split(corrupted_chunk[0])[1]

                # search for the region file
                backup_region_path = glob(join(backup, region_file))[0]
                region_file = corrupted_chunk[0]
                if backup_region_path:
                    print "Backup region file found in: {0} \nfixing...".format(backup_region_path)

                    # get the chunk
                    backup_region_file = region.RegionFile(backup_region_path)
                    working_chunk = check_chunk(backup_region_file, x, z)
                    backup_region_file.__del__()
                    
                    if isinstance(working_chunk, nbt.TAG_Compound):
                        # the chunk exists and is non-corrupted, fix it!
                        tofix_region_file = region.RegionFile(region_file)
                        tofix_region_file.write_chunk(corrupted_chunk[1], corrupted_chunk[2],working_chunk)
                        tofix_region_file.__del__
                        Fixed = True
                        counter_fixed += 1
                        delete_chunks.remove(corrupted_chunk)
                        print "Chunk fixed using backup dir: {0}".format(backup)
                        break
                        
                    elif working_chunk == None:
                        print "The chunk doesn't exists in this backup directory: {0}".format(backup)
                        # The chunk doesn't exists in the region file
                        continue
                        
                    elif working_chunk == -1:
                        # The chunk is corrupted
                        print "The chunk is corrupted in this backup directory: {0}".format(backup)
                        continue
                        
        print "\n{0} fixed chunks of a total of {1} corrupted chunks".format(counter_fixed, len(bad_chunks))
                        
    else:
        delete_chunks = bad_chunks


    if args.delete:
        region_file = region_path = None # variable inizializations
        counter = 0
        
        print "{0:#^60}".format(' Deleting chunks ')

        for corrupted_chunk in delete_chunks:
            x = corrupted_chunk[1]
            z = corrupted_chunk[2]
            
            region_path = corrupted_chunk[0]
            region_file = region.RegionFile(region_path)
            region_file.unlink_chunk(x, z)
            counter += 1
            print "Chunk deleted!"
            region_file.__del__
        
        print "Deleted {0} corrupted chunks".format(counter)
        
if __name__ == '__main__':
    exit(main())

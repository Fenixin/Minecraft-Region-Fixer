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

from optparse import OptionParser, OptionGroup
from glob import glob
from os.path import join, split, exists, getsize
import sys
import nbt.region as region
import zlib
import gzip
import nbt.nbt as nbt

import world
from scan import scan_all_players, scan_level, scan_all_mcr_files


def parse_backup_list(world_backup_dirs):
    """ Generates a list with the input of backup dirs containing the 
    world objects of valid world directories."""

    backup_worlds = []
    directories = world_backup_dirs.split(',')
    for world_dir in directories:
        if exists(world_dir):
            w = world.World(world_dir)
            if not w.all_mcr_files and not w.level_file:
                print "[ATTENTION] The directory \"{0}\" doesn't look like a minecraft world folder.".format(world_dir)
            else:
                backup_worlds.append(w)
        else:
            print "[ATTENTION] The directory \"{0}\" doesn't exist".format(world_dir)
    return backup_worlds


def parse_chunk_list(chunk_list, world_obj):
    """ Generate a list of chunks to use with world.delete_chunk_list.
    
    It takes a list of global chunk coordinates and generates a list of
    tuples containing:

    (region fullpath, chunk X, chunk Z)

    """

    parsed_list = []
    for line in chunk_list:
        try:
            chunk = eval(line)
        except:
            print "The chunk {0} is not valid.".format(line)
            continue
        region_name = world.get_chunk_region(chunk[0], chunk[1])
        fullpath = join(world_obj.world_path, "region", region_name)
        if fullpath in world_obj.all_mcr_files:
            parsed_list.append((fullpath, chunk[0], chunk[1]))
        else:
            print "The chunk {0} should be in the region file {1} and this region files doesn't extist!".format(chunk, fullpath)

    return parsed_list


def main():
    
    usage = 'usage: %prog [options] <world-path>'
    epilog = 'Copyright (C) 2011  Alejandro Aguilera (Fenixin) \
    https://github.com/Fenixin/Minecraft-Region-Fixer                                        \
    This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.txt. This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt for details.'

    parser = OptionParser(description='Script to check the integrity of Minecraft worlds and fix them when possible. It uses NBT by twoolie. \
                                            Author: Alejandro Aguilera (Fenixin). \
                                            Sponsored by: NITRADO Servers (http://nitrado.net)',\
    prog = 'region-fixer', version='0.0.5', usage=usage, epilog=epilog)

    parser.add_option('--backups', '-b', metavar = '<backups>', type = str, dest = 'backups', help = 'List of backup directories of the Minecraft \
                                        world to use to fix corrupted chunks and/or wrong located chunks. Warning! This script is not going \
                                        to check if it \'s the same world, so be careful! \
                                        This argument can be a comma separated list (but never with spaces between elements!).', default = None)
    parser.add_option('--replace-corrupted','--rc', dest = 'fix_corrupted', action='store_true', \
                                            help = 'Tries to replace the corrupted chunks using the backups directories', default = False)
    parser.add_option('--replace-wrong-located','--rw', dest = 'fix_wrong_located', action='store_true', \
                                            help = 'Tries to replace the wrong located chunks using the backups directories', default = False)
    parser.add_option('--delete-corrupted', '--dc', action = 'store_true', help = '[WARNING!] This option deletes! And deleting can make you lose data, so be careful! :P \
                                            This option will delete all the corrupted chunks. Used with --replace-corrupted or --replace-wrong-located it will delete all the non-replaced chunks.', default = False)
    parser.add_option('--delete-wrong-located', '--dw', action = 'store_true', help = '[WARNING!] This option deletes! The same as --delete-corrupted but for \
                                            wrong located chunks', default = False)
    parser.add_option('--delete-entities', '--de', action = 'store_true', help = '[WARNING!] This option deletes! This deletes ALL the entities of chunks with more entities than --entity-limit (500 by default). In a Minecraft world entities are mobs and items dropped in the grond, items in chests and other stuff won\'t be touched. Read the README for more info. Region-Fixer will delete the entities when scanning so you can stop and resume the process', default = False, dest = 'delete_entities')
    parser.add_option('--entity-limit', '--el', action = 'store', type = int, help = 'Specify the limit for the --delete-entities option (default = 500).', dest = 'entity_limit', default = 500,)
    parser.add_option('--processes', '-p', action = 'store', type = int, help = 'Set the number of workers to use for scanning region files. Default is to not use multiprocessing at all', default = 1)
    parser.add_option('--verbose', '-v',action='store_true',help='Don\'t use progress bar, print a line per scanned region file. The letters mean c: corrupted, w: wrong located, t: total of chunks')
    parser.add_option('--summary', '-s',action='store_true',help='Prints a summary with all the found problems in region files.', default = False)
    
    # Other options
    other_group = OptionGroup(parser, "Others", "This option is a different part of the program and is incompatible with the options above. You can't mix int he same line this options with above ones.")
    
    other_group.add_option('--delete-list', metavar = 'delete_list', type = str, help = 'Takes a file with a chunk list inside and deletes the chunks in that list. The list is formed by one chunk\
                                                                                        per line with the format (x,z). [INFO] if you use this option the world won\'t be scanned.', default = None)
    parser.add_option_group(other_group)
    (options, args) = parser.parse_args()

    # Only the world directory goes to args

    if not args:
        parser.error("No world path specified! Use --help for a complete list of options.")
        sys.exit()
    elif len(args) > 1:
        parser.error("Only one world dirctory needed!")
        sys.exit()

    world_path = args[0]
    if not exists(world_path):
        parser.error("The world path doesn't exists!")
        sys.exit()

    # Check basic options incompatibilities
    if options.backups and not (options.fix_corrupted or options.fix_wrong_located):
        parser.error("The option --backups needs one of the --fix-* options")
    
    if not options.backups and (options.fix_corrupted or options.fix_wrong_located):
        parser.error("The options --fix-* need the --backups option")

    if options.entity_limit <= 0:
        parser.error("The entity limit must be at least 1!")

    print "Welcome to Region Fixer!"


    # do things with the option args
    if options.backups: # create a list of worlds containing the backup of the region files
        backup_worlds = parse_backup_list(options.backups)
        if not backup_worlds:
            print "[WARNING] No valid backup directories found, won't fix any chunk."
    else:
        backup_worlds = []

    # scan the world dir
    print "Scanning directory..."

    w = world.World(world_path)

    if not w.level_file:
        print "Warning: No \'level.dat\' file found!"

    if not w.normal_mcr_files:
        print "Warning: No region files found in the \"region\" directory!"

    if not w.nether_mcr_files:
        print "Info: No nether dimension in the world directory."

    if not w.all_mcr_files and not w.level_file:
        print "Error: No region files to scan!"
        sys.exit()
        
    if w.player_files:
        print "There are {0} region files and {1} player files in the world directory.".format(len(w.normal_mcr_files) + len(w.nether_mcr_files), len(w.player_files))
    else:
        print "There are {0} region files in the world directory.".format(len(w.normal_mcr_files) + len(w.nether_mcr_files))

    region_files = w.all_mcr_files

    # The program starts
    if options.delete_list: # Delete the given list of chunks
        try:
            list_file = file(options.delete_list)
        except:
            print 'List file not found!'
            sys.exit()

        delete_list = parse_chunk_list(list_file, w)
        
        print "{0:#^60}".format(' Deleting the chunks on the list ')
        
        counter = w.delete_chunk_list(delete_list)
        print "Done!"
        
        print "Deleted {0} chunks".format(counter)
        
    else:
        # check the level.dat file and the *.dat files in players directory

        print "\n{0:#^60}".format(' Scanning level.dat ')

        if not w.level_file:

            print "[WARNING!] \'level.dat\' doesn't exist!"
        else:
            scan_level(w)
            if len(w.level_problems) == 0:
                print "\'level.dat'\ is redable"
            else:
                print "[WARNING!]: \'level.dat\' is corrupted with the following error/s:"
                for e in w.level_problems: print e,


        print "\n{0:#^60}".format(' Scanning player files ')
        
        if not w.player_files:
            print "Info: No player files to scan."
        else:
            scan_all_players(w)
        
            if not w.player_with_problems:
                print "All player files are readable."
            else:
                for player in w.player_with_problems:
                    print "Warning: Player file \"{0}.dat\" has problems: {1}".format(player, w.player_status[player])

        # check for corrupted chunks
        print "\n{0:#^60}".format(' Scanning region files ')

        scan_all_mcr_files(w, options)

        corrupted = w.count_problems(w.CORRUPTED)
        wrong_located = w.count_problems(w.WRONG_LOCATED)
        
        print "\nFound {0} corrupted and {1} wrong located chunks of a total of {2}\n".format(
            corrupted, wrong_located, w.num_chunks)

        # Try to fix corrupted chunks with the backup copy
        if backup_worlds:
            if options.fix_corrupted:
                print "{0:#^60}".format(' Trying to fix corrupted chunks ')
                fixed = w.replace_problematic_chunks(backup_worlds, w.CORRUPTED)
                print "\n{0} fixed chunks of a total of {1} corrupted chunks".format(fixed, corrupted)
            
            if options.fix_wrong_located:
                print "{0:#^60}".format(' Trying to fix wrong located chunks ')
                fixed = w.replace_problematic_chunks(backup_worlds, w.WRONG_LOCATED)
                print "\n{0} fixed chunks of a total of {1} wrong located chunks".format(fixed, wrong_located)

        corrupted = w.count_problems(w.CORRUPTED)
        wrong_located = w.count_problems(w.WRONG_LOCATED)

        # delete bad chunks! (if asked for)
        if options.delete_corrupted and corrupted:
            
            print "{0:#^60}".format(' Deleting  corrupted chunks ')

            print "... ",
            counter = w.remove_problematic_chunks(w.CORRUPTED)
            print "Done!"
            
            print "Deleted {0} corrupted chunks".format(counter)
        
        
        if options.delete_wrong_located and wrong_located:
            
            print "{0:#^60}".format(' Deleting wrong located chunks ')
            
            print "... ",
            counter = w.remove_problematic_chunks(w.WRONG_LOCATED)
            print "Done!"
            
            print "Deleted {0} wrong located chunks".format(counter)
        
        if options.summary:
            print "\n{0:#^60}".format(' Summary of found problems ')
            for mcr in w.mcr_problems:
                print split(mcr)[1] + ":"
                for chunk in w.mcr_problems[mcr]:
                    print "    chunk ",chunk," :",
                    for problem in w.mcr_problems[mcr][chunk]:
                        if problem == w.CORRUPTED:
                            print "Corrupted"
                        elif problem == w.WRONG_LOCATED:
                            print "Wrong located"
                        elif problem == w.TOO_MUCH_ENTITIES:
                            print "Too much entities"
                print
                


if __name__ == '__main__':
    main()

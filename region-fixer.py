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

from multiprocessing import freeze_support
from optparse import OptionParser, OptionGroup
from os.path import join, split, exists, isfile
from getpass import getpass
import sys


import world
from scan import scan_regionset, scan_world
from interactive import interactive_loop
from util import entitle, table, is_bare_console


def parse_paths(args):
    # parese the list of region files and worlds paths
    world_list = []
    region_list = []
    warning = False
    for arg in args:
        if arg[-4:] == ".mca":
            region_list.append(arg)
        elif arg[-4:] == ".mcr": # ignore pre-anvil region files
            if not warning:
                print "Warning: Region-Fixer only works with anvil format region files. Ignoring *.mcr files"
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
                print "Warning: \"{0}\" is not a file. Skipping it and scanning the rest.".format(f)
        else:
            print "Warning: The region file {0} doesn't exists. Skipping it and scanning the rest.".format(f)
    region_list = region_list_tmp

    # init the world objects
    world_list = parse_world_list(world_list)

    return world_list, world.RegionSet(region_list = region_list)

def parse_world_list(world_path_list):
    """ Parses a world list checking if they exists and are a minecraft
        world folders """
    
    # TODO expand bash folders
    tmp = []
    for d in world_path_list:
        if exists(d):
            w = world.World(d)
            if w.isworld:
                tmp.append(w)
            else:
                print "Warning: The folder {0} doesn't look like a minecraft world. I'll skip it.".format(d)
        else:
            print "Warning: The folder {0} doesn't exist. I'll skip it.".format(d)
    return tmp

def parse_backup_list(world_backup_dirs):
    """ Generates a list with the input of backup dirs containing the
    world objects of valid world directories."""

    directories = world_backup_dirs.split(',')
    backup_worlds = parse_world_list(directories)
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
        if fullpath in world_obj.all_mca_files:
            parsed_list.append((fullpath, chunk[0], chunk[1]))
        else:
            print "The chunk {0} should be in the region file {1} and this region files doesn't extist!".format(chunk, fullpath)

    return parsed_list

def main():

    usage = 'usage: %prog [options] <world-path> <other-world-path> ... <region-files> ...'
    epilog = 'Copyright (C) 2011  Alejandro Aguilera (Fenixin) \
    https://github.com/Fenixin/Minecraft-Region-Fixer                                        \
    This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.txt. This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt for details.'

    parser = OptionParser(description='Script to check the integrity of Minecraft worlds and fix them when possible. It uses NBT by twoolie. \
                                            Author: Alejandro Aguilera (Fenixin). \
                                            Sponsored by: NITRADO Servers (http://nitrado.net)',\
    prog = 'region-fixer', version='0.1.0', usage=usage, epilog=epilog)

    parser.add_option('--backups', '-b', help = 'List of backup directories of the Minecraft world to use to fix corrupted chunks and/or wrong located chunks. Warning! Region-Fixer is not going to check if it\'s the same world, be careful! This argument can be a comma separated list (but never with spaces between elements!). This option can be only used scanning one world.',\
        metavar = '<backups>', type = str, dest = 'backups', default = None)

    parser.add_option('--replace-corrupted','--rc', help = 'Tries to replace the corrupted chunks using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_corrupted', action='store_true')

    parser.add_option('--replace-wrong-located','--rw', help = 'Tries to replace the wrong located chunks using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_wrong_located', action='store_true')

    parser.add_option('--replace-entities','--re    ', help = 'Tries to replace the chunks with too many entities using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_entities', action='store_true')

    parser.add_option('--replace-shared-offset','--rs    ', help = 'Tries to replace the chunks with a shared offset using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_shared_offset', action='store_true')

    parser.add_option('--replace-too-small','--rt    ', help = 'Tries to replace the region files that are too small to be actually be a region file using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_too_small', action='store_true')

    parser.add_option('--delete-corrupted', '--dc', help = '[WARNING!] This option deletes! This option will delete all the corrupted chunks. Used with --replace-corrupted or --replace-wrong-located it will delete all the non-replaced chunks.',\
        action = 'store_true', default = False)

    parser.add_option('--delete-wrong-located', '--dw', help = '[WARNING!] This option deletes! The same as --delete-corrupted but for wrong located chunks',\
        action = 'store_true', default = False, dest='delete_wrong_located')

    parser.add_option('--delete-entities', '--de', help = '[WARNING!] This option deletes! This option deletes ALL the entities in chunks with more entities than --entity-limit (300 by default). In a Minecraft entities are mostly mobs and items dropped in the grond, items in chests and other stuff won\'t be touched. Read the README for more info. Region-Fixer will delete the entities while scanning so you can stop and resume the process',\
        action = 'store_true', default = False, dest = 'delete_entities')

    parser.add_option('--delete-shared-offset', '--fo', help = 'This option will delete all the chunk with status shared offset. It will remove the region header for the false chunk, note that you don\'t loos any chunk doing this.',\
        action = 'store_true', default = False, dest = 'delete_shared_offset')

    parser.add_option('--entity-limit', '--el', help = 'Specify the limit for the --delete-entities option (default = 300).',\
        dest = 'entity_limit', default = 300, action = 'store', type = int)

    parser.add_option('--delete-too-small', '--dt', help = 'Removes any region files found to be too small to actually be a region file.',\
        dest ='delete_too_small', default = False, action = 'store_true')

    parser.add_option('--processes', '-p',  help = 'Set the number of workers to use for scanning. (defaulta = 1, not use multiprocessing at all)',\
        action = 'store', type = int, default = 1)

    parser.add_option('--verbose', '-v', help='Don\'t use a progress bar, instead print a line per scanned region file with results information. The letters mean c: corrupted; w: wrong located; t: total of chunksm; tme: too many entities problem',\
        action='store_true', default = False)

    parser.add_option('--interactive', '-i',help='Enter in interactive mode, where you can scan, see the problems, and fix them in a terminal like mode',\
        dest = 'interactive',default = False, action='store_true',)

    parser.add_option('--log', '-l',help='Saves a log of all the problems found in the spicifyed file. The log file contains all the problems found with this information: region file, chunk coordinates and problem. Use \'-\' as name to show the log at the end of the scan.',\
        type = str, default = None, dest = 'summary')

    (options, args) = parser.parse_args()

    if is_bare_console():
        print
        print "Minecraft Region Fixer is a command line aplication, if you want to run it"
        print "you need to open a command line (cmd.exe in the start menu in windows 7)."
        print 
        getpass("Press enter to continue:")
        return 1

    # Args are world_paths and region files
    if not args:
        parser.error("No world paths or region files specified! Use --help for a complete list of options.")

    world_list, region_list = parse_paths(args)

    if not (world_list or region_list):
        print ("Error: No worlds or region files to scan!")
        return 1

    # Check basic options compatibilities
    any_replace_option = options.replace_corrupted or options.replace_wrong_located or options.delete_corrupted or options.delete_wrong_located or options.replace_shared_offset
    if options.interactive or options.summary:
        if any_replace_option:
            parser.error("Can't use the options --replace-* , --delete-* and --log with --interactive.")

    else: # not options.interactive
        if options.backups:
            if not any_replace_option:
                parser.error("The option --backups needs at least one of the --replace-* options")
            else:
                if (len(region_list.regions) > 0):
                    parser.error("The input should be only one world and you intruduced {0} individual region files.".format(len(region_list.regions)))
                elif (len(world_list) > 1):
                    parser.error("The input should be only one world and you intruduced {0} worlds.".format(len(world_list)))

        if not options.backups and any_replace_option:
            parser.error("The options --replace-* need the --backups option")

    if options.entity_limit < 0:
        parser.error("The entity limit must be at least 0!")

    print "\nWelcome to Region Fixer!"

    # do things with the option options args
    if options.backups: # create a list of worlds containing the backups of the region files
        backup_worlds = parse_backup_list(options.backups)
        if not backup_worlds:
            print "[WARNING] No valid backup directories found, won't fix any chunk."
    else:
        backup_worlds = []


    # The program starts
    if options.interactive:
        # TODO: WARNING, NEEDS CHANGES FOR WINDOWS. check while making the windows exe
        c = interactive_loop(world_list, region_list, options, backup_worlds)
        c.cmdloop()


    else:
        summary_text = ""

        # scan the separate region files
        if len(region_list.regions) > 0:
            print entitle("Scanning separate region files", 0)
            scan_regionset(region_list, options)

            print region_list.generate_report(True)

            # TODO summary seems to be broken
            if options.summary:
                summary_text += "\n"
                summary_text += entitle("Separate region files")
                summary_text += "\n"
                t = region_list.summary()
                if t:
                    summary_text += t
                else:
                    summary_text += "No problems found.\n\n"


        # scan all the world folders
        for world_obj in world_list:
            print entitle(' Scanning world: {0} '.format(world_obj.get_name()),0)

            scan_world(world_obj, options)
            
            print world_obj.generate_report(standalone = True)
            corrupted, wrong_located, entities_prob, shared_prob, total_chunks, too_small_region, unreadable_region, total_regions = world_obj.generate_report(standalone = False)
            
            if backup_worlds:
                # Try to replace bad chunks with a backup copy
                if options.replace_corrupted:
                    if world_obj.count_chunks(world.CHUNK_CORRUPTED):
                        print "{0:#^60}".format(' Trying to replace corrupted chunks ')
                        fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CHUNK_CORRUPTED, options)
                        print "\n{0} replaced chunks of a total of {1} corrupted chunks".format(fixed, corrupted)
                    else: print "No corrupted chunks to replace!"

                if options.replace_wrong_located:
                    if world_obj.count_chunks(world.CHUNK_WRONG_LOCATED):
                        print "{0:#^60}".format(' Trying to replace wrong located chunks ')
                        fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CHUNK_WRONG_LOCATED, options)
                        print "\n{0} replaced chunks of a total of {1} wrong located chunks".format(fixed, wrong_located)
                    else: print "No wrong located chunks to replace!"

                if options.replace_entities:
                    if world_obj.count_chunks(world.CHUNK_TOO_MANY_ENTITIES):
                        print "{0:#^60}".format(' Trying to replace chunks with too many entities ')
                        fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CHUNK_TOO_MANY_ENTITIES, options)
                        print "\n{0} replaced chunks of a total of {1} chunks with too many entities".format(fixed, entities_prob)
                    else: print "No chunks with too many entities to replace!"

                if options.replace_shared_offset:
                    if world_obj.count_chunks(world.CHUNK_SHARED_OFFSET):
                        print "{0:#^60}".format(' Trying to replace chunks with shared offsets ')
                        fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CHUNK_SHARED_OFFSET, options)
                        print "\n{0} replaced chunks of a total of {1} chunks with shared offsets".format(fixed, shared_prob)
                    else: print "No chunks with shared offsets to replace!"
                # TODO: to replace this properly we have to scan the whole region file in the backup world
                
                if options.replace_too_small:
                    print "Hay en total {0} regiones pequeñas".format(world_obj.count_regions(world.REGION_TOO_SMALL))
                    if world_obj.count_regions(world.REGION_TOO_SMALL):
                        print "{0:#^60}".format(' Trying to replace too small region files ')
                        fixed = world_obj.replace_problematic_regions(backup_worlds, world.REGION_TOO_SMALL, options)
                        print "\n{0} replaced regions of a total of {1} too small regions files.".format(fixed, too_small_region)
                    else: print "No too small region files to replace!"

            elif any_replace_option: # and not options.backups:
                print "No backup worlds found, won't replace any chunks/region files!"

            # delete bad chunks!
            if options.delete_corrupted:
                if corrupted:
                    print "{0:#^60}".format(' Deleting  corrupted chunks ')
                    counter = world_obj.remove_problematic_chunks(world.CHUNK_CORRUPTED)
                    print "Done!"

                    print "Deleted {0} corrupted chunks".format(counter)
                else:
                    print "No corrupted chunks to delete!"

            if options.delete_wrong_located:
                if wrong_located:
                    print "{0:#^60}".format(' Deleting wrong located chunks ')
                    counter = world_obj.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
                    print "Done!"

                    print "Deleted {0} wrong located chunks".format(counter)
                else:
                    print "No wrong located chunks to delete!"

            if options.delete_too_small:
                if too_small_region:
                    print "{0:#^60}".format(' Deleting too small region files ')
                    counter = world_obj.remove_problematic_regions(world.REGION_TOO_SMALL)
                    print "Done!"

                    print "Deleted {0} too small region files".format(counter)
                else:
                    print "No too small region files to delete!"

            if options.delete_shared_offset:
                if shared_prob:
                    print "{0:#^60}".format(' Deleting chunks with shared offset ')
                    counter = world_obj.remove_problematic_chunks(world.CHUNK_SHARED_OFFSET)
                    print "Done!"

                    print "Deleted {0} ".format(counter)
                else:
                    print "No shared offset chunks to delete!"
            
            # print a summary for this world
            if options.summary:
                summary_text += world_obj.summary()

        # summary seems to be broken
        if options.summary == '-':
            print summary_text
        elif options.summary != None:
            try:
                f = open(options.summary, 'w')
                f.write(summary_text)
                f.write('\n')
                f.close()
                print "Log file saved in \'{0}\'.".format(options.summary)
            except:
                print "Something went wrong while saving the log file!"

    return 0


if __name__ == '__main__':
    freeze_support()
    value = main()
    sys.exit(value)

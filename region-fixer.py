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
from getpass import getpass
import sys

import world
from scan import scan_regionset, scan_world
from interactive import interactive_loop
from util import entitle, is_bare_console, parse_world_list, parse_paths, parse_backup_list

def delete_bad_chunks(options, scanned_obj):
    """ Takes a scanned object (world object or regionset object) and 
    the options given to region-fixer, it deletes all the chunks with
    problems iterating through all the possible problems. """
    print # a blank line
    options_delete = [options.delete_corrupted, options.delete_wrong_located, options.delete_entities, options.delete_shared_offset]
    deleting = zip(options_delete, world.CHUNK_PROBLEMS)
    for delete, problem in deleting:
        status = world.CHUNK_STATUS_TEXT[problem]
        total = scanned_obj.count_chunks(problem)
        if delete:
            if total:
                text = ' Deleting chunks with status: {0} '.format(status)
                print "{0:#^60}".format(text)
                counter = scanned_obj.remove_problematic_chunks(problem)

                print "\nDeleted {0} chunks with status: {1}".format(counter,status)
            else:
                print "No chunks to delete with status: {0}".format(status)

def delete_bad_regions(options, scanned_obj):
    """ Takes an scanned object (world object or regionset object) and 
    the options give to region-fixer, it deletes all the region files
    with problems iterating through all the possible problems. """
    print # a blank line
    options_delete = [options.delete_too_small]
    deleting = zip(options_delete, world.REGION_PROBLEMS)
    for delete, problem in deleting:
        status = world.REGION_STATUS_TEXT[problem]
        total = scanned_obj.count_regions(problem)
        if delete:
            if total:
                text = ' Deleting regions with status: {0} '.format(status)
                print "{0:#^60}".format(text)
                counter = scanned_obj.remove_problematic_regions(problem)

                print "Deleted {0} regions with status: {1}".format(counter,status)
            else:
                print "No regions to delete with status: {0}".format(status)

def main():

    usage = 'usage: %prog [options] <world-path> <other-world-path> ... <region-files> ...'
    epilog = 'Copyright (C) 2011  Alejandro Aguilera (Fenixin) \
    https://github.com/Fenixin/Minecraft-Region-Fixer                                        \
    This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.txt. This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt for details.'

    parser = OptionParser(description='Script to check the integrity of Minecraft worlds and fix them when possible. It uses NBT by twoolie. Author: Alejandro Aguilera (Fenixin)',\
    prog = 'region-fixer', version='0.1.2', usage=usage, epilog=epilog)

    parser.add_option('--backups', '-b', help = 'List of backup directories of the Minecraft world to use to fix corrupted chunks and/or wrong located chunks. Warning! Region-Fixer is not going to check if it\'s the same world, be careful! This argument can be a comma separated list (but never with spaces between elements!). This option can be only used scanning one world.',\
        metavar = '<backups>', type = str, dest = 'backups', default = None)

    parser.add_option('--replace-corrupted','--rc', help = 'Tries to replace the corrupted chunks using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_corrupted', action='store_true')

    parser.add_option('--replace-wrong-located','--rw', help = 'Tries to replace the wrong located chunks using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_wrong_located', action='store_true')

    parser.add_option('--replace-entities','--re', help = 'Tries to replace the chunks with too many entities using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_entities', action='store_true')

    parser.add_option('--replace-shared-offset','--rs', help = 'Tries to replace the chunks with a shared offset using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_shared_offset', action='store_true')

    parser.add_option('--replace-too-small','--rt', help = 'Tries to replace the region files that are too small to be actually be a region file using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_too_small', action='store_true')

    parser.add_option('--delete-corrupted', '--dc', help = '[WARNING!] This option deletes! This option will delete all the corrupted chunks. Used with --replace-corrupted or --replace-wrong-located it will delete all the non-replaced chunks.',\
        action = 'store_true', default = False)

    parser.add_option('--delete-wrong-located', '--dw', help = '[WARNING!] This option deletes! The same as --delete-corrupted but for wrong located chunks',\
        action = 'store_true', default = False, dest='delete_wrong_located')

    parser.add_option('--delete-entities', '--de', help = '[WARNING!] This option deletes! This option deletes ALL the entities in chunks with more entities than --entity-limit (300 by default). In a Minecraft entities are mostly mobs and items dropped in the grond, items in chests and other stuff won\'t be touched. Read the README for more info. Region-Fixer will delete the entities while scanning so you can stop and resume the process',\
        action = 'store_true', default = False, dest = 'delete_entities')

    parser.add_option('--delete-shared-offset', '--ds', help = '[WARNING!] This option deletes! This option will delete all the chunk with status shared offset. It will remove the region header for the false chunk, note that you don\'t loos any chunk doing this.',\
        action = 'store_true', default = False, dest = 'delete_shared_offset')

    parser.add_option('--delete-too-small', '--dt', help = '[WARNING!] This option deletes! Removes any region files found to be too small to actually be a region file.',\
        dest ='delete_too_small', default = False, action = 'store_true')

    parser.add_option('--entity-limit', '--el', help = 'Specify the limit for the --delete-entities option (default = 300).',\
        dest = 'entity_limit', default = 300, action = 'store', type = int)

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
    any_chunk_replace_option = options.replace_corrupted or options.replace_wrong_located or options.replace_entities or options.replace_shared_offset
    any_chunk_delete_option = options.delete_corrupted or options.delete_wrong_located or options.delete_entities or options.delete_shared_offset
    any_region_replace_option = options.replace_too_small
    any_region_delete_option = options.delete_too_small

    if options.interactive or options.summary:
        if any_chunk_replace_option or any_region_replace_option:
            parser.error("Can't use the options --replace-* , --delete-* and --log with --interactive. You can choose all this while in the interactive mode.")

    else: # not options.interactive
        if options.backups:
            if not any_chunk_replace_option and not any_region_replace_option:
                parser.error("The option --backups needs at least one of the --replace-* options")
            else:
                if (len(region_list.regions) > 0):
                    parser.error("You can't use the replace options while scanning sparate region files. The input should be only one world and you intruduced {0} individual region files.".format(len(region_list.regions)))
                elif (len(world_list) > 1):
                    parser.error("You can't use the replace options while scanning multiple worlds. The input should be only one world and you intruduced {0} worlds.".format(len(world_list)))

        if not options.backups and any_chunk_replace_option:
            parser.error("The options --replace-* need the --backups option")

    if options.entity_limit < 0:
        parser.error("The entity limit must be at least 0!")

    print "\nWelcome to Region Fixer!"
    print "(version: {0})".format(parser.version)

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
            
            # delete chunks
            delete_bad_chunks(options, region_list)

            # delete region files
            delete_bad_regions(options, region_list)

            # verbose log
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
            print 
            
            # replace chunks
            if backup_worlds and not len(world_list) > 1:
                options_replace = [options.replace_corrupted, options.replace_wrong_located, options.replace_entities, options.replace_shared_offset]
                replacing = zip(options_replace, world.CHUNK_PROBLEMS_ITERATOR)
                for replace, (problem, status, arg) in replacing:
                    if replace:
                        total = world_obj.count_chunks(problem)
                        if total:
                            text = " Replacing chunks with status: {0} ".format(status)
                            print "{0:#^60}".format(text)
                            fixed = world_obj.replace_problematic_chunks(backup_worlds, problem, options)
                            print "\n{0} replaced of a total of {1} chunks with status: {2}".format(fixed, total, status)
                        else: print "No chunks to replace with status: {0}".format(status)

            elif any_chunk_replace_option and not backup_worlds:
                print "Info: Won't replace any chunk."
                print "No backup worlds found, won't replace any chunks/region files!"
            elif any_chunk_replace_option and backup_worlds and len(world_list) > 1:
                print "Info: Won't replace any chunk."
                print "Can't use the replace options while scanning more than one world!"

            # replace region files
            if backup_worlds and not len(world_list) > 1:
                options_replace = [options.replace_too_small]
                replacing = zip(options_replace, world.REGION_PROBLEMS_ITERATOR)
                for replace, (problem, status, arg) in replacing:
                    if replace:
                        total = world_obj.count_regions(problem)
                        if total:
                            text = " Replacing regions with status: {0} ".format(status)
                            print "{0:#^60}".format(text)
                            fixed = world_obj.replace_problematic_regions(backup_worlds, problem, options)
                            print "\n{0} replaced of a total of {1} regions with status: {2}".format(fixed, total, status)
                        else: print "No region to replace with status: {0}".format(status)

            elif any_region_replace_option and not backup_worlds:
                print "Info: Won't replace any regions."
                print "No valid backup worlds found, won't replace any chunks/region files!"
                print "Note: You probably inserted some backup worlds with the backup option but they are probably no valid worlds, the most common issue is wrong path."
            elif any_region_replace_option and backup_worlds and len(world_list) > 1:
                print "Info: Won't replace any regions."
                print "Can't use the replace options while scanning more than one world!"

            # delete chunks
            delete_bad_chunks(options, world_obj)
            
            # delete region files
            delete_bad_regions(options, world_obj)

            # print a summary for this world
            if options.summary:
                summary_text += world_obj.summary()

        # verbose log text
        if options.summary == '-':
            print "\nPrinting log:\n"
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

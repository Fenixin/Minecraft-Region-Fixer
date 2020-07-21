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

import argparse
from getpass import getpass
from multiprocessing import freeze_support
import sys


from regionfixer_core.bug_reporter import BugReporter
import regionfixer_core.constants as c
from regionfixer_core.interactive import InteractiveLoop
from regionfixer_core.scan import (console_scan_world,
                                   console_scan_regionset,
                                   ChildProcessException)
from regionfixer_core.util import entitle, is_bare_console
from regionfixer_core.version import version_string
from regionfixer_core import world



def fix_bad_chunks(options, scanned_obj):
    """ Fixes chunks that can be repaired.

    Keywords arguments:
    options -- argparse arguments, the whole argparse.ArgumentParser() object
    scanned_obj -- this can be a RegionSet or World objects from world.py

    Returns nothing.

    It will fix the chunks as requested by options and modify the RegionSet and World objects
    with the new fixed chunks.
    """

    print("")
    total = scanned_obj.count_chunks(c.CHUNK_MISSING_ENTITIES_TAG)
    problem = c.CHUNK_MISSING_ENTITIES_TAG
    status = c.CHUNK_STATUS_TEXT[c.CHUNK_MISSING_ENTITIES_TAG]
    # In the same order as in FIXABLE_CHUNK_PROBLEMS
    options_fix = [options.fix_corrupted,
                   options.fix_missing_tag,
                   options.fix_wrong_located]
    fixing = list(zip(options_fix, c.FIXABLE_CHUNK_PROBLEMS))
    for fix, problem in fixing:
        status = c.CHUNK_STATUS_TEXT[problem]
        total = scanned_obj.count_chunks(problem)
        if fix:
            if total:
                text = ' Repairing chunks with status: {0} '.format(status)
                print(("\n{0:#^60}".format(text)))
                counter = scanned_obj.fix_problematic_chunks(problem)
                print(("\nRepaired {0} chunks with status: {1}".format(counter,
                                                                     status)))
            else:
                print(("No chunks to fix with status: {0}".format(status)))


def delete_bad_chunks(options, scanned_obj):
    """ Takes a scanned object and deletes all the bad chunks.

    Keywords arguments
    options -- argparse arguments, the whole argparse.ArgumentParser() object
    scanned_obj -- this can be a RegionSet or World objects from world.py

    Returns nothing.

    This function will deletes all the chunks with problems
    iterating through all the possible problems and using the
    options given.
    """

    print("")
    # In the same order as in CHUNK_PROBLEMS
    options_delete = [options.delete_corrupted,
                      options.delete_wrong_located,
                      options.delete_entities,
                      options.delete_shared_offset,
                      options.delete_missing_tag]
    deleting = list(zip(options_delete, c.CHUNK_PROBLEMS))
    for delete, problem in deleting:
        status = c.CHUNK_STATUS_TEXT[problem]
        total = scanned_obj.count_chunks(problem)
        if delete:
            if total:
                text = ' Deleting chunks with status: {0} '.format(status)
                print(("\n{0:#^60}".format(text)))
                counter = scanned_obj.remove_problematic_chunks(problem)
                print(("\nDeleted {0} chunks with status: {1}".format(counter,
                                                                      status)))
            else:
                print(("No chunks to delete with status: {0}".format(status)))


def delete_bad_regions(options, scanned_obj):
    """  Takes a scanned object and deletes all bad region files.
    
    Keywords arguments:
    options -- argparse arguments, the whole argparse.ArgumentParser() object
    scanned_obj -- this can be a RegionSet or World objects from world.py

    Returns nothing.
    
    Takes an scanned object (World object or RegionSet object) and
    the options given to region-fixer and it deletes all the region files
    with problems iterating through all the possible problems.
    """

    print("")
    options_delete = [options.delete_too_small]
    deleting = list(zip(options_delete, c.REGION_PROBLEMS))
    for delete, problem in deleting:
        status = c.REGION_STATUS_TEXT[problem]
        total = scanned_obj.count_regions(problem)
        if delete:
            if total:
                text = ' Deleting regions with status: {0} '.format(status)
                print(("{0:#^60}".format(text)))
                counter = scanned_obj.remove_problematic_regions(problem)
                print(("Deleted {0} regions with status: {1}".format(counter,
                                                                     status)))
            else:
                print(("No regions to delete with status: {0}".format(status)))


def main():
    usage = ('%(prog)s [options] <world-path> '
             '<other-world-path> ... <region-files> ...')
    epilog = ('Copyright (C) 2020  Alejandro Aguilera (Fenixin)\n'
              'https://github.com/Fenixin/Minecraft-Region-Fixer\n'
              'This program comes with ABSOLUTELY NO WARRANTY; for '
              'details see COPYING.txt. This is free software, and you '
              'are welcome to redistribute it under certain conditions; '
              'see COPYING.txt for details.')

    parser = argparse.ArgumentParser(description=('Program to check the integrity of '
                                                  'Minecraft worlds and fix them when '
                                                  'possible. It uses NBT by twoolie. '
                                                  'Author: Alejandro Aguilera (Fenixin)'),
                                     prog='region_fixer',
                                     usage=usage,
                                     epilog=epilog)


    parser.add_argument('--backups',
                        '-b',
                        help=('List of backup directories of the Minecraft world '
                              'to use to fix corrupted chunks and/or wrong located '
                              'chunks. Warning! Region-Fixer is not going to check if'
                              'it\'s the same world, be careful! This argument can be a'
                              ' comma separated list (but never with spaces between '
                              'elements!). This option can be only used scanning one '
                              'world.'),
                        metavar='<backups>',
                        type=str,
                        dest='backups',
                        default=None)

    parser.add_argument('--replace-corrupted',
                        '--rc',
                        help='Tries to replace the corrupted chunks using the backup'
                             ' directories. This option can be only used scanning one'
                             ' world.',
                        default=False,
                        dest='replace_corrupted',
                        action='store_true')

    parser.add_argument('--replace-wrong-located',
                        '--rw',
                        help='Tries to replace the wrong located chunks using the '
                             'backup directories. This option can be only used scanning'
                             ' one world.',
                        default=False,
                        dest='replace_wrong_located',
                        action='store_true')

    parser.add_argument('--replace-entities',
                        '--re',
                        help='Tries to replace the chunks with too many entities using '
                             'the backup directories. This option can be only used '
                             'scanning one world.',
                        default=False,
                        dest='replace_entities',
                        action='store_true')

    parser.add_argument('--replace-shared-offset',
                        '--rs',
                        help='Tries to replace the chunks with a shared offset using '
                             'the backup directories. This option can be only used'
                             'scanning one world.',
                        default=False,
                        dest='replace_shared_offset',
                        action='store_true')

    parser.add_argument('--replace-too-small',
                        '--rt',
                        help='Tries to replace the region files that are too small to '
                             'be actually be a region file using the backup '
                             'directories. This option can be only used scanning one '
                             'world.',
                        default=False,
                        dest='replace_too_small',
                        action='store_true')

    parser.add_argument('--delete-corrupted',
                        '--dc',
                        help='[WARNING!] This option deletes! This option will delete '
                             'all the corrupted chunks. Used with --replace-corrupted '
                             'or --replace-wrong-located it will delete all the '
                             'non-replaced chunks.',
                        action='store_true',
                        default=False)

    parser.add_argument('--delete-wrong-located',
                        '--dw',
                        help=('[WARNING!] This option deletes!'
                              'The same as --delete-corrupted but for wrong '
                              'located chunks'),
                        action='store_true',
                        default=False,
                        dest='delete_wrong_located')

    parser.add_argument('--delete-entities',
                        '--de',
                        help='[WARNING!] This option deletes! This option deletes ALL '
                             'the entities in chunks with more entities than '
                             '--entity-limit (300 by default). In a Minecraft '
                             'entities are mostly mobs and items dropped in the '
                             'ground, items in chests and other stuff won\'t be '
                             'touched. Read the README for more info. Region-Fixer '
                             'will delete the entities while scanning so you can '
                             'stop and resume the process',
                        action='store_true',
                        default=False,
                        dest='delete_entities')

    parser.add_argument('--delete-shared-offset',
                        '--ds',
                        help='[WARNING!] This option deletes! This option will delete '
                             'all the chunk with status shared offset. It will remove '
                             'the region header for the false chunk, note that you '
                             'don\'t loos any chunk doing this.',
                        action='store_true',
                        default=False,
                        dest='delete_shared_offset')

    parser.add_argument('--delete-missing-tag',
                        '--dmt',
                        help='[WARNING!] This option deletes! Removes any chunks '
                             'with the mandatory entities tag missing.',
                        dest='delete_missing_tag',
                        default=False,
                        action='store_true')

    parser.add_argument('--fix-corrupted',
                        '--fc',
                        help='Tries to fix chunks that are corrupted. This will try to decompress as much as possible from'
                            'the data stream and see if the size is reasonable.',
                        dest='fix_corrupted',
                        default=False,
                        action='store_true')

    parser.add_argument('--fix-missing-tag',
                        '--fm',
                        help='Fixes chunks that have the Entities tag missing. This will add the missing tag.',
                        dest='fix_missing_tag',
                        default=False,
                        action='store_true')

    parser.add_argument('--fix-wrong-located',
                        '--fw',
                        help='Fixes chunks that have that are wrong located. This will save them in the coordinates '
                            'stored in their data.',
                        dest='fix_wrong_located',
                        default=False,
                        action='store_true')

    parser.add_argument('--delete-too-small',
                        '--dt',
                        help='[WARNING!] This option deletes! Removes any region files '
                             'found to be too small to actually be a region file.',
                        dest='delete_too_small',
                        default=False,
                        action='store_true')

    parser.add_argument('--entity-limit',
                        '--el',
                        help='Specify the limit for the --delete-entities option '
                             '(default = 300).',
                        dest='entity_limit',
                        default=300,
                        action='store',
                        type=int)

    parser.add_argument('--processes',
                        '-p',
                        help='Set the number of workers to use for scanning. (default '
                             '= 1, not use multiprocessing at all)',
                        action='store',
                        type=int,
                        default=1)

    parser.add_argument('--verbose',
                        '-v',
                        help='Don\'t use a progress bar, instead print a line per '
                             'scanned region file with results information. The '
                             'letters mean c: corrupted; w: wrong located; t: total of '
                             'chunks; tme: too many entities problem',
                        action='store_true',
                        default=False)

    #===========================================================================
    # parser.add_argument('--interactive',
    #                     '-i',
    #                     help='Enter in interactive mode, where you can scan, see the '
    #                          'problems, and fix them in a terminal like mode',
    #                     dest='interactive',
    #                     default=False,
    #                     action='store_true', )
    #===========================================================================

    parser.add_argument('--log',
                        '-l',
                        help='Saves a log of all the problems found in the specified '
                             'file. The log file contains all the problems found with '
                             'this information: region file, chunk coordinates and '
                             'problem. Use \'-\' as name to show the log at the end '
                             'of the scan.',
                        type=str,
                        default=None,
                        dest='summary')

    parser.add_argument('paths',
                        help='List with world or region paths',
                        nargs='*')

    args = parser.parse_args()

    if sys.version_info[0] != 3:
        print("")
        print("Minecraft Region Fixer only works with python 3.x")
        print(("(And you just tried to run it in python {0})".format(sys.version)))
        print("")
        return c.RV_CRASH

    if is_bare_console():
        print("")
        print("Minecraft Region Fixer is a command line application and \n"
              "you have just double clicked it. If you really want to run \n"
              "the command line interface you have to use a command prompt.\n"
              "Run cmd.exe in the run window.\n\n")
        print("")
        getpass("Press enter to continue:")
        return c.RV_CRASH


    world_list, regionset = world.parse_paths(args.paths)

    # print greetings an version number
    print("\nWelcome to Region Fixer!")
    print(("(v {0})".format(version_string)))

    # Check if there are valid worlds to scan
    if not (world_list or regionset):
        print('Error: No worlds or region files to scan! Use '
                     '--help for a complete list of options.')
        return c.RV_NOTHING_TO_SCAN

    # Check basic options compatibilities
    any_chunk_replace_option = args.replace_corrupted or \
        args.replace_wrong_located or \
        args.replace_entities or \
        args.replace_shared_offset
    any_region_replace_option = args.replace_too_small

    if False or args.summary: # removed interactive mode args.interactive
        if any_chunk_replace_option or any_region_replace_option:
            parser.error('Error: Can\'t use the options --replace-* , --delete-* with '
                         '--log')

    else:
        # Not options.interactive
        if args.backups:
            if not any_chunk_replace_option and not any_region_replace_option:
                parser.error('Error: The option --backups needs at least one of the '
                             '--replace-* options')
            else:
                if len(regionset) > 0:
                    parser.error('Error: You can\'t use the replace options while scanning '
                                 'separate region files. The input should be only one '
                                 'world and you introduced {0} individual region '
                                 'files.'.format(len(regionset)))
                elif len(world_list) > 1:
                    parser.error('Error: You can\'t use the replace options while scanning '
                                 'multiple worlds. The input should be only one '
                                 'world and you introduced {0} '
                                 'worlds.'.format(len(world_list)))

        if not args.backups and any_chunk_replace_option:
            parser.error("Error: The options --replace-* need the --backups option")

    if args.entity_limit < 0:
        parser.error("Error: The entity limit must be at least 0!")

    # Do things with the option options args
    # Create a list of worlds containing the backups of the region files
    if args.backups:
        backup_worlds = world.parse_backup_list(args.backups)
        if not backup_worlds:
            print('[WARNING] No valid backup directories found, won\'t fix '
                  'any chunk.')
    else:
        backup_worlds = []

    # The scanning process starts
    found_problems_in_regionsets = False
    found_problems_in_worlds = False
    if False: # removed args.interactive
        ci = InteractiveLoop(world_list, regionset, args, backup_worlds)
        ci.cmdloop()
        return c.RV_OK
    else:
        summary_text = ""
        # Scan the separate region files

        if len(regionset) > 0:

            console_scan_regionset(regionset, args.processes, args.entity_limit,
                                   args.delete_entities, args.verbose)
            print((regionset.generate_report(True)))

            # Delete chunks
            delete_bad_chunks(args, regionset)

            # Delete region files
            delete_bad_regions(args, regionset)

            # fix chunks
            fix_bad_chunks(args, regionset)

            # Verbose log
            if args.summary:
                summary_text += "\n"
                summary_text += entitle("Separate region files")
                summary_text += "\n"
                t = regionset.summary()
                if t:
                    summary_text += t
                else:
                    summary_text += "No problems found.\n\n"

            # Check if problems have been found
            if regionset.has_problems:
                found_problems_in_regionsets = True

        # scan all the world folders

        for w in world_list:
            w_name = w.get_name()
            print((entitle(' Scanning world: {0} '.format(w_name), 0)))

            console_scan_world(w, args.processes, args.entity_limit,
                               args.delete_entities, args.verbose)

            print("")
            print((entitle('Scan results for: {0}'.format(w_name), 0)))
            print((w.generate_report(True)))
            print("")

            # Replace chunks
            if backup_worlds and len(world_list) <= 1:
                del_ent = args.delete_entities
                ent_lim = args.entity_limit
                options_replace = [args.replace_corrupted,
                                   args.replace_wrong_located,
                                   args.replace_entities,
                                   args.replace_shared_offset]
                replacing = list(zip(options_replace, c.CHUNK_PROBLEMS_ITERATOR))
                for replace, (problem, status, arg) in replacing:
                    if replace:
                        total = w.count_chunks(problem)
                        if total:
                            text = " Replacing chunks with status: {0} ".format(status)
                            print(("{0:#^60}".format(text)))
                            fixed = w.replace_problematic_chunks(backup_worlds, problem, ent_lim, del_ent)
                            print(("\n{0} replaced of a total of {1} chunks with status: {2}".format(fixed, total, status)))
                        else:
                            print(("No chunks to replace with status: {0}".format(status)))

            elif any_chunk_replace_option and not backup_worlds:
                print("Info: Won't replace any chunk.")
                print("No backup worlds found, won't replace any chunks/region files!")
            elif any_chunk_replace_option and backup_worlds and len(world_list) > 1:
                print("Info: Won't replace any chunk.")
                print("Can't use the replace options while scanning more than one world!")

            # replace region files
            if backup_worlds and len(world_list) <= 1:
                del_ent = args.delete_entities
                ent_lim = args.entity_limit
                options_replace = [args.replace_too_small]
                replacing = list(zip(options_replace, c.REGION_PROBLEMS_ITERATOR))
                for replace, (problem, status, arg) in replacing:
                    if replace:
                        total = w.count_regions(problem)
                        if total:
                            text = " Replacing regions with status: {0} ".format(status)
                            print(("{0:#^60}".format(text)))
                            fixed = w.replace_problematic_regions(backup_worlds, problem, ent_lim, del_ent)
                            print(("\n{0} replaced of a total of {1} regions with status: {2}".format(fixed, total, status)))
                        else:
                            print(("No region to replace with status: {0}".format(status)))

            elif any_region_replace_option and not backup_worlds:
                print("Info: Won't replace any regions.")
                print("No valid backup worlds found, won't replace any chunks/region files!")
                print("Note: You probably inserted some backup worlds with the backup option but they are probably no valid worlds, the most common issue is wrong path.")
            elif any_region_replace_option and backup_worlds and len(world_list) > 1:
                print("Info: Won't replace any regions.")
                print("Can't use the replace options while scanning more than one world!")

            # delete chunks
            delete_bad_chunks(args, w)

            # delete region files
            delete_bad_regions(args, w)

            # fix chunks
            fix_bad_chunks(args, w)

            # print a summary for this world
            if args.summary:
                summary_text += w.summary()

            # check if problems have been found
            if w.has_problems:
                found_problems_in_worlds = True

        # verbose log text
        if args.summary == '-':
            print("\nPrinting log:\n")
            print(summary_text)
        elif args.summary is not None:
            try:
                f = open(args.summary, 'w')
                f.write(summary_text)
                f.write('\n')
                f.close()
                print(("Log file saved in \'{0}\'.".format(args.summary)))
            except:
                print("Something went wrong while saving the log file!")

    if found_problems_in_regionsets or found_problems_in_worlds:
        return c.RV_BAD_WORLD

    return c.RV_OK


if __name__ == '__main__':
    ERROR_MSG = "\n\nOps! Something went really wrong and regionfixer crashed.\n"
    QUESTION_TEXT = ('Do you want to send an anonymous bug report to the region fixer ftp?\n'
                     '(Answering no will print the bug report)')
    had_exception = False
    auto_reported = False
    value = 0

    try:
        freeze_support()
        value = main()

    except SystemExit as e:
        # sys.exit() was called within the program
        had_exception = False
        value = e.code

    except ChildProcessException as e:
        had_exception = True
        print(ERROR_MSG)
        bug_sender = BugReporter(e.printable_traceback)
        # auto_reported = bug_sender.ask_and_send(QUESTION_TEXT)
        bug_report = bug_sender.error_str
        value = c.RV_CRASH

    except Exception as e:
        had_exception = True
        print(ERROR_MSG)
        # Traceback will be taken in init
        bug_sender = BugReporter()
        # auto_reported = bug_sender.ask_and_send(QUESTION_TEXT)
        bug_report = bug_sender.error_str
        value = c.RV_CRASH

    finally:
        if had_exception and not auto_reported:
            print("")
            print("Bug report:")
            print("")
            print(bug_report)
        elif had_exception and auto_reported:
            print("Bug report uploaded successfully")
        sys.exit(value)

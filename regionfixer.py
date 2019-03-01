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
from optparse import OptionParser
from getpass import getpass
import sys

from regionfixer_core import world
from regionfixer_core.scan import console_scan_world, console_scan_regionset,\
                                  ChildProcessException
from regionfixer_core.interactive import InteractiveLoop
from regionfixer_core.util import entitle, is_bare_console, parse_paths,\
                                  parse_backup_list
from regionfixer_core.version import version_string
from regionfixer_core.bug_reporter import BugReporter


def delete_bad_chunks(options, scanned_obj):
    """ Takes a scanned object (world object or regionset object) and
    the options given to region-fixer, it deletes all the chunks with
    problems iterating through all the possible problems. """
    print("")
    # In the same order as in CHUNK_PROBLEMS
    options_delete = [options.delete_corrupted,
                      options.delete_wrong_located,
                      options.delete_entities,
                      options.delete_shared_offset]
    deleting = list(zip(options_delete, world.CHUNK_PROBLEMS))
    for delete, problem in deleting:
        status = world.CHUNK_STATUS_TEXT[problem]
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
    """ Takes an scanned object (world object or regionset object) and
    the options give to region-fixer, it deletes all the region files
    with problems iterating through all the possible problems. """
    print("")
    options_delete = [options.delete_too_small]
    deleting = list(zip(options_delete, world.REGION_PROBLEMS))
    for delete, problem in deleting:
        status = world.REGION_STATUS_TEXT[problem]
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

    usage = ('usage: \n%prog [options] <world-path> '
             '<other-world-path> ... <region-files> ...')
    epilog = ('Copyright (C) 2011  Alejandro Aguilera (Fenixin)\n'
              'https://github.com/Fenixin/Minecraft-Region-Fixer\n'
              'This program comes with ABSOLUTELY NO WARRANTY; for '
              'details see COPYING.txt. This is free software, and you '
              'are welcome to redistribute it under certain conditions; '
              'see COPYING.txt for details.')

    parser = OptionParser(description=('Program to check the integrity of '
                                       'Minecraft worlds and fix them when '
                                       'possible. It uses NBT by twoolie. '
                                       'Author: Alejandro Aguilera (Fenixin)'),
                          prog='region_fixer',
                          version=version_string,
                          usage=usage,
                          epilog=epilog)

    add_option = parser.add_option

    add_option('--backups',
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

    add_option('--replace-corrupted',
               '--rc',
               help='Tries to replace the corrupted chunks using the backup'
                    ' directories. This option can be only used scanning one'
                    ' world.',
               default=False,
               dest='replace_corrupted',
               action='store_true')

    add_option('--replace-wrong-located',
               '--rw',
               help='Tries to replace the wrong located chunks using the '
                    'backup directories. This option can be only used scanning'
                    ' one world.',
               default=False,
               dest='replace_wrong_located',
               action='store_true')

    add_option('--replace-entities',
               '--re',
               help='Tries to replace the chunks with too many entities using '
                    'the backup directories. This option can be only used '
                    'scanning one world.',
               default=False,
               dest='replace_entities',
               action='store_true')

    add_option('--replace-shared-offset',
               '--rs',
               help='Tries to replace the chunks with a shared offset using '
                    'the backup directories. This option can be only used'
                    'scanning one world.',
               default=False,
               dest='replace_shared_offset',
               action='store_true')

    add_option('--replace-too-small',
               '--rt',
               help='Tries to replace the region files that are too small to '
                    'be actually be a region file using the backup '
                    'directories. This option can be only used scanning one '
                    'world.',
               default=False,
               dest='replace_too_small',
               action='store_true')

    add_option('--delete-corrupted',
               '--dc',
               help='[WARNING!] This option deletes! This option will delete '
                    'all the corrupted chunks. Used with --replace-corrupted '
                    'or --replace-wrong-located it will delete all the '
                    'non-replaced chunks.',
               action='store_true',
               default=False)

    add_option('--delete-wrong-located',
               '--dw',
               help=('[WARNING!] This option deletes!'
                     'The same as --delete-corrupted but for wrong '
                     'located chunks'),
               action='store_true',
               default=False,
               dest='delete_wrong_located')

    add_option('--delete-entities',
               '--de',
               help='[WARNING!] This option deletes! This option deletes ALL '
                    'the entities in chunks with more entities than '
                    '--entity-limit (300 by default). In a Minecraft '
                    'entities are mostly mobs and items dropped in the '
                    'grond, items in chests and other stuff won\'t be '
                    'touched. Read the README for more info. Region-Fixer '
                    'will delete the entities while scanning so you can '
                    'stop and resume the process',
               action='store_true',
               default=False,
               dest='delete_entities')

    add_option('--delete-shared-offset',
               '--ds',
               help='[WARNING!] This option deletes! This option will delete '
                    'all the chunk with status shared offset. It will remove '
                    'the region header for the false chunk, note that you '
                    'don\'t loos any chunk doing this.',
               action='store_true',
               default=False,
               dest='delete_shared_offset')

    add_option('--delete-too-small',
               '--dt',
               help='[WARNING!] This option deletes! Removes any region files '
                    'found to be too small to actually be a region file.',
               dest='delete_too_small',
               default=False,
               action='store_true')

    add_option('--entity-limit',
               '--el',
               help='Specify the limit for the --delete-entities option '
                    '(default = 300).',
               dest='entity_limit',
               default=300,
               action='store',
               type=int)

    add_option('--processes',
               '-p',
               help='Set the number of workers to use for scanning. (defaulta '
                    '= 1, not use multiprocessing at all)',
               action='store',
               type=int,
               default=1)

    add_option('--verbose',
               '-v',
               help='Don\'t use a progress bar, instead print a line per '
                    'scanned region file with results information. The '
                    'letters mean c: corrupted; w: wrong located; t: total of '
                    'chunksm; tme: too many entities problem',
              action='store_true',
              default=False)

    add_option('--interactive',
               '-i',
               help='Enter in interactive mode, where you can scan, see the '
                    'problems, and fix them in a terminal like mode',
               dest='interactive',
               default=False,
               action='store_true',)

    add_option('--log',
               '-l',
               help='Saves a log of all the problems found in the spicifyed '
                    'file. The log file contains all the problems found with '
                    'this information: region file, chunk coordinates and '
                    'problem. Use \'-\' as name to show the log at the end '
                    'of the scan.',
               type=str,
               default=None,
               dest='summary')

    (options, args) = parser.parse_args()
    o = options

    if sys.version_info[0] > 5:
        print("")
        print("Minecraft Region Fixer only works with python 2.x")
        print(("(And you just tried to run it in python {0})".format(sys.version)))
        print("")
        return 1

    if is_bare_console():
        print("")
        print("Minecraft Region Fixer hast a command line aplication and a GUI\n"
              "(Graphic User Interface) and you have just double clicked the\n"
              "command line interface. If you really want to run the command line\n"
              "interface you have to use a command prompt (cmd.exe)\n\n"
              "You can also run the gui, double click regionfixer_gui.py instead!")
        print("")
        getpass("Press enter to continue:")
        return 1

    # Args are world_paths and region files
    if not args:
        parser.error('No world paths or region files specified! Use '
                     '--help for a complete list of options.')

    world_list, regionset = parse_paths(args)

    if not (world_list or regionset):
        print ("Error: No worlds or region files to scan!")
        return 1

    # Check basic options compatibilities
    any_chunk_replace_option = o.replace_corrupted or \
                               o.replace_wrong_located or \
                               o.replace_entities or \
                               o.replace_shared_offset
    any_chunk_delete_option = o.delete_corrupted or \
                              o.delete_wrong_located or \
                              o.delete_entities or \
                              o.delete_shared_offset
    any_region_replace_option = o.replace_too_small
    any_region_delete_option = o.delete_too_small

    error = parser.error


    if o.interactive or o.summary:
        if any_chunk_replace_option or any_region_replace_option:
            error('Can\'t use the options --replace-* , --delete-* and '
                  '--log with --interactive. You can choose all this '
                  'while in the interactive mode.')

    else:
        # Not options.interactive
        if o.backups:
            if not any_chunk_replace_option and not any_region_replace_option:
                error('The option --backups needs at least one of the '
                      '--replace-* options')
            else:
                if (len(regionset.regions) > 0):
                    error('You can\'t use the replace options while scanning '
                          'separate region files. The input should be only one '
                          'world and you introduced {0} individual region '
                          'files.'.format(len(regionset.regions)))
                elif (len(world_list) > 1):
                    error('You can\'t use the replace options while scanning '
                          'multiple worlds. The input should be only one '
                          'world and you introduced {0} '
                          'worlds.'.format(len(world_list)))

        if not o.backups and any_chunk_replace_option:
            error("The options --replace-* need the --backups option")

    if o.entity_limit < 0:
        error("The entity limit must be at least 0!")

    print("\nWelcome to Region Fixer!")
    print(("(version: {0})".format(parser.version)))

    # Do things with the option options args
    # Create a list of worlds containing the backups of the region files
    if o.backups:
        backup_worlds = parse_backup_list(o.backups)
        if not backup_worlds:
            print ('[WARNING] No valid backup directories found, won\'t fix '
                   'any chunk.')
    else:
        backup_worlds = []

    # The program starts
    if o.interactive:
        c = InteractiveLoop(world_list, regionset, o, backup_worlds)
        c.cmdloop()
    else:
        summary_text = ""
        # Scan the separate region files
        if len(regionset.regions) > 0:
            console_scan_regionset(regionset, o.processes, o.entity_limit,
                                   o.delete_entities, o.verbose)
            print((regionset.generate_report(True)))

            # Delete chunks
            delete_bad_chunks(options, regionset)

            # Delete region files
            delete_bad_regions(options, regionset)

            # Verbose log
            if options.summary:
                summary_text += "\n"
                summary_text += entitle("Separate region files")
                summary_text += "\n"
                t = regionset.summary()
                if t:
                    summary_text += t
                else:
                    summary_text += "No problems found.\n\n"

        # scan all the world folders
        for w in world_list:
            w_name = w.get_name()
            print((entitle(' Scanning world: {0} '.format(w_name), 0)))

            console_scan_world(w, o.processes, o.entity_limit,
                               o.delete_entities, o.verbose)

            print("")
            print((entitle('Scan results for: {0}'.format(w_name), 0)))
            print((w.generate_report(True)))

#             corrupted, wrong_located, entities_prob, shared_prob,\
#             total_chunks, too_small_region, unreadable_region, total_regions\
#             = w.generate_report(standalone = False)

            print("")
            # Replace chunks
            if backup_worlds and not len(world_list) > 1:
                del_ent = options.delete_entities
                ent_lim = options.entity_limit
                options_replace = [o.replace_corrupted,
                                   o.replace_wrong_located,
                                   o.replace_entities,
                                   o.replace_shared_offset]
                replacing = list(zip(options_replace, world.CHUNK_PROBLEMS_ITERATOR))
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
            if backup_worlds and not len(world_list) > 1:
                del_ent = options.delete_entities
                ent_lim = options.entity_limit
                options_replace = [o.replace_too_small]
                replacing = list(zip(options_replace, world.REGION_PROBLEMS_ITERATOR))
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
            delete_bad_chunks(options, w)

            # delete region files
            delete_bad_regions(options, w)

            # print a summary for this world
            if options.summary:
                summary_text += w.summary()

        # verbose log text
        if options.summary == '-':
            print("\nPrinting log:\n")
            print(summary_text)
        elif options.summary != None:
            try:
                f = open(options.summary, 'w')
                f.write(summary_text)
                f.write('\n')
                f.close()
                print(("Log file saved in \'{0}\'.".format(options.summary)))
            except:
                print("Something went wrong while saving the log file!")

    return 0


if __name__ == '__main__':
    ERROR_MSG = "\n\nOps! Something went really wrong and regionfixer crashed. I can try to send an automatic bug rerpot if you wish.\n\n"
    QUESTION_TEXT = ('Do you want to send an anonymous bug report to the region fixer ftp?\n'
                     '(Answering no will print the bug report)')
    had_exception = False
    auto_reported = False

    try:
        freeze_support()
        value = main()
        sys.exit(value)

    except ChildProcessException as e:
        had_exception = True
        print(ERROR_MSG)
        bug_sender = BugReporter(e.printable_traceback)
        #auto_reported = bug_sender.ask_and_send(QUESTION_TEXT)
        bug_report = bug_sender.error_str

    except Exception as e:
        had_exception = True
        print(ERROR_MSG)
        # Traceback will be taken in init
        bug_sender = BugReporter()
        #auto_reported = bug_sender.ask_and_send(QUESTION_TEXT)
        bug_report = bug_sender.error_str

    finally:
        if had_exception and not auto_reported:
            print("")
            print("Bug report:")
            print("")
            print(bug_report)
        elif had_exception and auto_reported:
            print("Bug report uploaded successfully")

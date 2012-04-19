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
import sys
from cmd import Cmd

import world
from scan import scan_all_players, scan_level, scan_regionset, scan_world

def parse_paths(args):
    # parese the list of region files and worlds paths
    world_list = []
    region_list = []
    for arg in args:
        if arg[-4:] == ".mca":
            region_list.append(arg)
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
    
    # check for the world folders
    world_list = parse_world_list(world_list)

    return world_list, world.RegionSet(region_list)


def parse_world_list(world_path_list):
    """ Parses a world list checking if they exists and are a minecraft
        world folders """
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
    
    usage = 'usage: %prog [options] <world-path> <region-files>'
    epilog = 'Copyright (C) 2011  Alejandro Aguilera (Fenixin) \
    https://github.com/Fenixin/Minecraft-Region-Fixer                                        \
    This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.txt. This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt for details.'

    parser = OptionParser(description='Script to check the integrity of Minecraft worlds and fix them when possible. It uses NBT by twoolie. \
                                            Author: Alejandro Aguilera (Fenixin). \
                                            Sponsored by: NITRADO Servers (http://nitrado.net)',\
    prog = 'region-fixer', version='0.0.9', usage=usage, epilog=epilog)

    parser.add_option('--backups', '-b', metavar = '<backups>', type = str, dest = 'backups', help = 'List of backup directories of the Minecraft \
                                        world to use to fix corrupted chunks and/or wrong located chunks. Warning! This script is not going \
                                        to check if it \'s the same world, so be careful! \
                                        This argument can be a comma separated list (but never with spaces between elements!).', default = None)
    parser.add_option('--replace-corrupted','--rc', dest = 'replace_corrupted', action='store_true', \
                                            help = 'Tries to replace the corrupted chunks using the backups directories', default = False)
    parser.add_option('--replace-wrong-located','--rw', dest = 'replace_wrong_located', action='store_true', \
                                            help = 'Tries to replace the wrong located chunks using the backups directories', default = False)
    parser.add_option('--delete-corrupted', '--dc', action = 'store_true', help = '[WARNING!] This option deletes! And deleting can make you lose data, so be careful! :P \
                                            This option will delete all the corrupted chunks. Used with --replace-corrupted or --replace-wrong-located it will delete all the non-replaced chunks.', default = False)
    parser.add_option('--delete-wrong-located', '--dw', action = 'store_true', help = '[WARNING!] This option deletes! The same as --delete-corrupted but for \
                                            wrong located chunks', default = False)
    parser.add_option('--delete-entities', '--de', action = 'store_true', help = '[WARNING!] This option deletes! This deletes ALL the entities of chunks with more entities than --entity-limit (500 by default). In a Minecraft world entities are mobs and items dropped in the grond, items in chests and other stuff won\'t be touched. Read the README for more info. Region-Fixer will delete the entities when scanning so you can stop and resume the process', default = False, dest = 'delete_entities')
    parser.add_option('--entity-limit', '--el', action = 'store', type = int, help = 'Specify the limit for the --delete-entities option (default = 500).', dest = 'entity_limit', default = 500,)
    parser.add_option('--processes', '-p', action = 'store', type = int, help = 'Set the number of workers to use for scanning region files. Default is to not use multiprocessing at all', default = 1)
    parser.add_option('--verbose', '-v',action='store_true',help='Don\'t use progress bar, print a line per scanned region file. The letters mean c: corrupted, w: wrong located, t: total of chunks')
    parser.add_option('--interactive', '-i',action='store_true',help='Scans the world and then enter in interactive mode, where you can write commands an do things',dest = 'interactive',default = False)
    parser.add_option('--summary', '-s',action='store_true',help='Prints a summary with all the found problems in region files.', default = False)
    
    # Other options
    other_group = OptionGroup(parser, "Others", "This option is a different part of the program and is incompatible with the options above. You can't mix int he same line this options with above ones.")
    
    other_group.add_option('--delete-list', metavar = 'delete_list', type = str, help = 'Takes a file with a chunk list inside and deletes the chunks in that list. The list is formed by one chunk\
                                                                                        per line with the format (x,z). [INFO] if you use this option the world won\'t be scanned.', default = None)
    parser.add_option_group(other_group)
    (options, args) = parser.parse_args()

    # Args are world_paths and region files
    if not args:
        parser.error("No world paths or region files specified! Use --help for a complete list of options.")

    world_list, region_list = parse_paths(args)
    
    if not (world_list or region_list):
        print ("Error: No worlds or region files to scan!")
        sys.exit(1)

    # Check basic options incompatibilities
    if options.interactive and (options.replace_corrupted or options.replace_wrong_located or options.delete_corrupted or options.delete_wrong_located):
        parser.error("The can't use the options --replace-* or --delete-* while entering in interactive mode.")
    
    else:
        if options.backups and not (options.replace_corrupted or options.replace_wrong_located):
            parser.error("The option --backups needs one of the --replace-* options")
        
        if not options.backups and (options.replace_corrupted or options.replace_wrong_located):
            parser.error("The options --replace-* need the --backups option")

        if options.entity_limit <= 0:
            parser.error("The entity limit must be at least 1!")

    print "Welcome to Region Fixer!"

    # do things with the option options args
    if options.backups: # create a list of worlds containing the backups of the region files
        backup_worlds = parse_backup_list(options.backups)
        if not backup_worlds:
            print "[WARNING] No valid backup directories found, won't fix any chunk."

# TODO hay que hacer una funcion
# que sea scan_region_set, o similar. Estaria bien tb mejorar todo lo de
# imprimir texto.

    # The program starts
    if options.delete_list: # Delete the given list of chunks
        # TODO esta función debería ctualizarse, una vez que cambiemos
        # a regionset y a multiworlds no tendrá sentido borrar una lista
        # de chunk con coordenadas globales... eliminar por completo la
        # opción?
        try:
            list_file = file(options.delete_list)
        except:
            print 'List file not found!'
            sys.exit(1)

        delete_list = parse_chunk_list(list_file, w)
        
        print "{0:#^60}".format(' Deleting the chunks on the list ')
        
        counter = w.delete_chunk_list(delete_list)
        print "Done!"
        
        print "Deleted {0} chunks".format(counter)
        
    else:
        for world_obj in world_list:
            # TODO hay que sustituir el nombre world por world_obj,
            # dejando world para referencias al módulo world.py
            
            print "\n"
            print "{0:#^60}".format('')
            if world_obj.name:
                print "{0:#^60}".format(' Scanning world: {0} '.format(world_obj.name))
            else:
                print "{0:#^60}".format(' Scanning world: {0} '.format(world_obj.world_path))
            print "{0:#^60}".format('')
            
            scan_world(world_obj, options)

            corrupted = world_obj.count_problems(world.CHUNK_CORRUPTED)
            wrong_located = world_obj.count_problems(world.CHUNK_WRONG_LOCATED)

            # Try to fix corrupted chunks with the backup copy
            if options.replace_corrupted or options.replace_wrong_located:
                if options.replace_corrupted:
                    print "{0:#^60}".format(' Trying to fix corrupted chunks ')
                    fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CORRUPTED)
                    print "\n{0} fixed chunks of a total of {1} corrupted chunks".format(fixed, corrupted)
                
                if options.replace_wrong_located:
                    print "{0:#^60}".format(' Trying to fix wrong located chunks ')
                    fixed = world_obj.replace_problematic_chunks(backup_worlds, world.WRONG_LOCATED)
                    print "\n{0} fixed chunks of a total of {1} wrong located chunks".format(fixed, wrong_located)

            # delete bad chunks! (if asked for)
            if options.delete_corrupted:
                if corrupted:
                    print "{0:#^60}".format(' Deleting  corrupted chunks ')

                    print "... ",
                    counter = world_obj.remove_problematic_chunks(world.CORRUPTED)
                    print "Done!"
                    
                    print "Deleted {0} corrupted chunks".format(counter)
                else:
                    print "No corrupted chunks to delete!"
            
            if options.delete_wrong_located:
                if wrong_located:
                    print "{0:#^60}".format(' Deleting wrong located chunks ')
                    
                    print "... ",
                    counter = world_obj.remove_problematic_chunks(world.WRONG_LOCATED)
                    print "Done!"
                    
                    print "Deleted {0} wrong located chunks".format(counter)
                else:
                    print "No wrong located chunks to delete!"

        if options.summary:
            print "\n{0:#^60}".format(' Summary of found problems ')
            text = summary(world_list[0], [world_list[0].CORRUPTED, world_list[0].WRONG_LOCATED, world_list[0].TOO_MUCH_ENTITIES])
            print text

        # Go to interactive mode?
        if options.interactive:
            # TODO make interactive mode incompatible with noraml mode
            ########################################################
            #~ import readline # interactive prompt with history 
            # WARNING NEEDS CHANGES FOR WINDOWS
            c = interactive_loop(w)
            c.cmdloop()


def summary(world, problems):
    # add a summary to file, and multiworld or multi regionset support
    w = world
    text = ''
    for mcr in w.mcr_problems:
        write = False
        chunk_problems = []
        for chunk in w.mcr_problems[mcr]:
            for p in w.mcr_problems[mcr][chunk]:
                # first check if we need to print this
                if p in problems:
                    write = True
                    chunk_problems.append((chunk, p))
        
        if write:
            # now print text for the region file
            text += split(mcr)[1] + ":\n"
            for c in chunk_problems:
                chunk = c[0]
                problem = c[1]
                text += "\tchunk " + str(c) + " :"
                if problem in problems:
                    if problem == w.CORRUPTED:
                        text += " corrupted\n"
                    elif problem == w.WRONG_LOCATED:
                        text += " wrong located\n"
                    elif problem == w.TOO_MUCH_ENTITIES:
                        text += " too much entities\n"
        if len(text) == 0:
            text = "No chunks with this problem."
    return text

class interactive_loop(Cmd):

# some TODO ideas:
# worlds are now stored in a list, add a "scan" command.
    def __init__(self, world):
        Cmd.__init__(self)
        self.w = world
        self.prompt = "-> "
        self.intro = "Minecraft Region-Fixer interactive mode."

    def do_list(self, arg):
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            if arg == "corrupted" or arg == "c":
                print summary(self.w, [self.w.CORRUPTED])
            elif arg == "wrong" or arg == "w" :
                print summary(self.w, [self.w.WRONG_LOCATED])
            elif arg == "entities" or arg == "e":
                print summary(self.w, [self.w.TOO_MUCH_ENTITIES])
            else:
                print "Unknown list."
    def complete_list(self, text, line, begidx, endidx):
        if text == '':
            return ["corrupted", "wrong", "entities"]
        elif text[0] == "c":
            return ["corrupted"]
        elif text[0] == "w":
            return ["wrong"]
        elif text[0] == "e":
            return ["entities"]
    def help_list(self):
        print "Prints a list of chunks with that problem, exmaple: \'list corrupted\' or \'list c\'. \nProblems are: corrupted, wrong, entities. You can aslo use the first letter."
    
    def do_quit(self, arg):
        print "Quitting."
        return True
    def help_quit(self):
        print "Quits interactive mode."
    
    def do_EOF(self, arg):
        print "Quitting."
        return True
    def help_EOF(self):
        print "Same as quit."
        
    def help_help(self):
        print "Prints help help."


if __name__ == '__main__':
    freeze_support()
    main()

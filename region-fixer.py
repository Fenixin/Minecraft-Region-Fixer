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
    
    # check for the world folders
    world_list = parse_world_list(world_list)

    return world_list, world.RegionSet(region_list = region_list)


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
    # TODO TODO TOOD
    # la ayuda de las opciones necesita una vuena actualización. Hay que decir que backups y replace no pueden usarse junto con varios mundos o con un 
    # regionset.
    
    
    
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
    # TODO: with interactive mode this needs a good revision
    if options.interactive and (options.replace_corrupted or options.replace_wrong_located or options.delete_corrupted or options.delete_wrong_located or options.summary):
        parser.error("Can't use the options --replace-* , --delete-* and --summary with interactive mode.")
    
    else:
        if options.backups:
            if not (options.replace_corrupted or options.replace_wrong_located):
                #~ parser.error("The option --backups needs one of the --replace-* options")
                pass
            else:
                if (len(region_list.regions) > 0):
                    parser.error("The input should be only one world and you intruduced {0} individual region files.".format(len(region_list.regions)))
                elif (len(world_list) > 1):
                    parser.error("The input should be only one world and you intruduced {0} worlds.".format(len(world_list)))
        
        #~ if not options.backups and (options.replace_corrupted or options.replace_wrong_located):
            #~ parser.error("The options --replace-* need the --backups option")

    if options.entity_limit < 0:
        parser.error("The entity limit must be at least 0!")

    print "Welcome to Region Fixer!"

    # do things with the option options args
    if options.backups: # create a list of worlds containing the backups of the region files
        backup_worlds = parse_backup_list(options.backups)
        if not backup_worlds:
            print "[WARNING] No valid backup directories found, won't fix any chunk."
    else:
        backup_worlds = []

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
        if len(region_list.regions) > 0:
            print "\n"
            print "{0:#^60}".format('')
            print "{0:#^60}".format(' Scanning region files ')
            print "{0:#^60}".format('')
            scan_regionset(region_list, options)
            
            corrupted = region_list.count_chunks(world.CHUNK_CORRUPTED)
            wrong_located = region_list.count_chunks(world.CHUNK_WRONG_LOCATED)
            entities_prob = region_list.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
            total = region_list.count_chunks()

            print "\nFound {0} corrupted, {1} wrong located chunks and {2} chunks with too much entities of a total of {3}\n".format(
                corrupted, wrong_located, entities_prob, total)
            
        for world_obj in world_list:
            print "\n"
            print "{0:#^60}".format('')
            print "{0:#^60}".format(' Scanning world: {0} '.format(world_obj.get_name()))
            print "{0:#^60}".format('')
            
            scan_world(world_obj, options)

            corrupted = world_obj.count_chunks(world.CHUNK_CORRUPTED)
            wrong_located = world_obj.count_chunks(world.CHUNK_WRONG_LOCATED)
            entities_prob = world_obj.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
            total = world_obj.count_chunks()

            print "\nFound {0} corrupted, {1} wrong located chunks and {2} chunks with too much entities of a total of {3}\n".format(
                corrupted, wrong_located, entities_prob, total)
            
            # Try to replace bad chunks with a backup copy
            if options.replace_corrupted or options.replace_wrong_located:
                if world_obj.count_chunks(world.CHUNK_CORRUPTED):
                    if options.replace_corrupted:
                        print "{0:#^60}".format(' Trying to replace corrupted chunks ')
                        fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CHUNK_CORRUPTED, options)
                        print "\n{0} replaced chunks of a total of {1} corrupted chunks".format(fixed, corrupted)
                else: print "No corrupted chunks to replace!"
                
                if world_obj.count_chunks(world.CHUNK_WRONG_LOCATED):
                    if options.replace_wrong_located:
                        print "{0:#^60}".format(' Trying to replace wrong located chunks ')
                        fixed = world_obj.replace_problematic_chunks(backup_worlds, world.CHUNK_WRONG_LOCATED, options)
                        print "\n{0} replaced chunks of a total of {1} wrong located chunks".format(fixed, wrong_located)
                else: print "No wrong located chuns to replace!"

            # delete bad chunks!
            # TODO this only works in the last world scanned!
            
            if options.delete_corrupted:
                if len(region_list.regions) > 0:
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
                    counter = world_obj.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
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
            c = interactive_loop(world_obj, options, backup_worlds)
            c.cmdloop()


def summary(world, problems):
    # TODO: This is completely broken
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
    # TODO ideas: a flag saying if the world
    # is scanned or not, make a separate file for all this: interactive.py,
    # remove entities command, set options command, pasar el scan del programa
    # y ejecutar aquí un sacan world
    def __init__(self, world, options, backup_worlds):
        Cmd.__init__(self)
        self.w = world
        self.options = options
        self.backup_worlds = backup_worlds
        self.prompt = "-> "
        self.intro = "Minecraft Region-Fixer interactive mode."
    
    # do
    def do_set(self,arg):
        # TODO: add the threads option!
        # the idea of this is to let change some of the scan options in
        # interactive mode.
        args = arg.split()
        if len(args) > 2 or len(args) == 0:
            print "Error: too many parameters."
        else:
            if args[0] in ("entity-limit"):
                if len(args) == 1:
                    print "entity-limit = {0}".format(self.options.entity_limit)
                else:
                    if int(args[1]) >= 0:
                        self.options.entity_limit = int(args[1])
                        print "entity-limit = {0}".format(args[1])
                    else:
                        print "Invalid value. Valid values are positive integers and zero"

            if args[0] in ("verbose", "v"):
                if len(args) == 1:
                    print "verbose = {0}".format(self.options.verbose)
                else:
                    if args[1] == "True":
                        self.options.verbose = True
                        print "verbose = {0}".format(args[1])
                    elif args[1] == "False":
                        self.options.verbose = False
                        print "verbose = {0}".format(args[1])
                    else:
                        print "Invalid value. Valid values are True and False."

    def do_count(self, arg):
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            if arg == "entities":
                n = self.w.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                print "Chunks with too much entities problem: {0}. (Note: entity limit = {1}).".format(n)
            elif arg == "corrupted":
                n = self.w.count_chunks(world.CHUNK_CORRUPTED)
                print "Corrupted chunks: {0}".format(n)
            elif arg == "wrong":
                n = self.w.count_chunks(world.CHUNK_WRONG_LOCATED)
                print "Wrong located chunks: {0}".format(n)
            elif arg == "all":
                nw = self.w.count_chunks(world.CHUNK_WRONG_LOCATED)
                nc = self.w.count_chunks(world.CHUNK_CORRUPTED)
                ne = self.w.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                
                print "Corrupted chunks: {0}".format(nc)
                print "Wrong located chunks: {0}".format(nw)
                print "Chunks with too much entities problem: {0}. (Note: entity limit = {1}).".format(ne, self.options.entity_limit)
                
            else:
                print "Unknown counter."

    def do_list(self, arg):
        # TODO: this is completely broken 
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            if arg == "corrupted":
                print summary(self.w, [world.CHUNK_CORRUPTED])
            elif arg == "wrong":
                print summary(self.w, [world.CHUNK_WRONG_LOCATED])
            elif arg == "entities":
                print summary(self.w, [world.CHUNK_TOO_MUCH_ENTITIES])
            else:
                print "Unknown list."

    def do_world(self, arg):
        # TODO how is this going to work?
        if len(arg) == 0:
            print self.w

    def do_scan(self, arg):
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            # TODO scan multiple worlds and multiple regionsets?
            if arg == "world":
                if self.w:
                    scan_world(self.w, self.options)
                else:
                    print "No world set!"
            elif arg == "regionset":
                if self.regionset:
                    scan_regionset(self.regionset)
                else:
                    print "No regionset set!"

    def do_remove_entities(self, arg):
        # TODO: once scanned you don't need scan it again to change the status of the chunks with too much entities, 
        # the number of entities is stored in the ScannedChunks obj. Make it in this way?
        # also, prompt a yes question?
        print "WARNING: This will delete all the entities in the chunks that have more entities than entity-limit. Note: you need to rescan your world if you change entity-limit. Are you sure you want to continue?"
        if len(arg.split()) > 0:
            print "Error: too many parameters."
        else:
            counter = self.w.remove_entities()
            print "Deleted {0} entities.".format(counter)
            
    def do_remove_chunks(self, arg):
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            if arg == "corrupted":
                self.w.remove_problematic_chunks(world.CHUNK_CORRUPTED)
            elif arg == "wrong":
                self.w.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
            elif arg == "entities":
                # TODO: there should be a remove_entities command and this one should be remove chunks
                # it'd be a good a idea to throw a big warning telling that you can delete the entities
                # without deleting the chunks.
                counter = self.w.remove_problematic_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                print "Done! Removed {0} chunks".format(counter)
            elif arg == "all":
                self.w.remove_problematic_chunks(world.CHUNK_CORRUPTED)
                self.w.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
                counter = self.w.remove_problematic_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
            else:
                print "Unknown argumen."

    def do_replace_chunks(self, arg):
        # TODO: parece que sustituye los chunks sin comprobar si están bien o no!
        # el replace necesita una buena revisión
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            if arg == "corrupted":
                if self.w.count_chunks(world.CHUNK_CORRUPTED):
                    counter = self.w.replace_problematic_chunks(self.backup_worlds, world.CHUNK_CORRUPTED, self.options)
                    print "Done! Replaced {0} chunks".format(counter)
                else:
                    print "No corrupted chunks to replace!"
            elif arg == "wrong":
                if self.w.count_chunks(world.CHUNK_WRONG_LOCATED):
                    counter = self.w.replace_problematic_chunks(self.backup_worlds, world.CHUNK_WRONG_LOCATED, self.options, )
                    print "Done! Replaced {0} chunks".format(counter)
                else:
                    print "No wrong located chunks to replace!"
            elif arg == "entities":
                if self.w.count_chunks(world.CHUNK_WRONG_LOCATED):
                    counter = self.w.replace_problematic_chunks(self.backup_worlds, world.CHUNK_TOO_MUCH_ENTITIES, self.options)
                    print "Done! Replaced {0} chunks".format(counter)
                else:
                    print "No chunks with too much entities problems to replace!"
            elif arg == "all":
                counter = self.w.replace_problematic_chunks(self.backup_worlds, world.CHUNK_CORRUPTED, self.options)
                counter += self.w.replace_problematic_chunks(self.backup_worlds, world.CHUNK_WRONG_LOCATED, self.options)
                counter += self.w.replace_problematic_chunks(self.backup_worlds, world.CHUNK_TOO_MUCH_ENTITIES, self.options)
                print "Done! Replaced {0} chunks".format(counter)
            else:
                print "Unknown argumen."

    def do_quit(self, arg):
        print "Quitting."
        return True

    def do_EOF(self, arg):
        print "Quitting."
        return True

    # complete
    # TODO: complete_scan
    def complete_arg(self, text, possible_args):
        l = []
        for arg in possible_args:
            if text in arg and arg.find(text) == 0:
                l.append(arg)
        return l

    def complete_set(self, text, line, begidx, endidx):
        possible_args = ('entity-limit','verbose')
        return self.complete_arg(text, possible_args)

    def complete_list(self, text, line, begidx, endidx):
        possible_args = ('corrupted','wrong','entities')
        return self.complete_arg(text, possible_args)

    def complete_count(self, text, line, begidx, endidx):
        possible_args = ('corrupted','wrong','entities','all')
        return self.complete_arg(text, possible_args)

    def complete_remove_chunks(self, text, line, begidx, endidx):
        possible_args = ('corrupted','wrong','entities','all')
        return self.complete_arg(text, possible_args)

    def complete_replace_chunks(self, text, line, begidx, endidx):
        possible_args = ('corrupted','wrong','entities','all')
        return self.complete_arg(text, possible_args)

    # help
    def help_set(self):
        print "Sets some variables used for the scan in interactive mode. You can set \"verbose\" and \"entity-limit\" in this way."
    def help_world(self):
        print "Prints current world set information."
    def help_scan(self):
        print "Scans the world set or the region set choosen when region-fixer is ran."
    def help_count(self):
        print "Prints out the number of chunks with that error. Example: \n\'count corrupted\'\n \
                prints the number of corrupted chunks in the world.\nProblems are: corrupted, wrong, entities or all"
    def help_remove_chunks(self):
        print "Removes bad chunks with the given problem. Problems are: corrupted, wrong, entities. Please, be careful, when used with the too much entities problem this will remove the chunks with too much entities problems, not the entities.\nUsage: \"remove_chunks c\"\nthis will remove the corrupted chunks"
    def help_replace_chunks(self):
        print "Replaces bad chunks with the given problem, using the backups directories. Problems are: corrupted, wrong, entities or all.\nUsage: \"replace_chunks corrupted\"\nthis will replace the corrupted chunks with the given backups"
    def help_list(self):
        print "Prints a list of chunks with that problem, exmaple: \
                \'list corrupted\' or \'list c\'. \n\
                Problems are: corrupted, wrong, entities and all."
    def help_quit(self):
        print "Quits interactive mode, exits region-fixer."
    def help_EOF(self):
        print "Quits interactive mode, exits region-fixer."
    def help_help(self):
        print "Prints help help."


if __name__ == '__main__':
    freeze_support()
    main()

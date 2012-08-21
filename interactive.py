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

import world

from cmd import Cmd
from scan import scan_world

class interactive_loop(Cmd):
    def __init__(self, world_list, regionset, options, backup_worlds):
        Cmd.__init__(self)
        self.world_list = world_list
        self.regionset = regionset
        self.world_names = [i.name for i in self.world_list]
        # if there's more than one world you have to set which one use
        # while in interactive mode using 'set workload'
        if len(self.world_list) == 1 and len(self.regionset) == 0:
            self.current = world_list[0]
        elif len(self.world_list) == 0 and len(self.regionset) > 1:
            self.current = self.regionset
        else:
            self.current = None
        self.options = options
        self.backup_worlds = backup_worlds
        self.prompt = "-> "
        self.intro = "Minecraft Region-Fixer interactive mode."
    
    # do
    def do_set(self,arg):
        # the idea of this is to let change some of the scan options in
        # interactive mode.
        args = arg.split()
        if len(args) > 2 or len(args) == 0:
            print "Error: too many parameters."
        else:
            if args[0] == "entity-limit":
                if len(args) == 1:
                    print "entity-limit = {0}".format(self.options.entity_limit)
                else:
                    if int(args[1]) >= 0:
                        self.options.entity_limit = int(args[1])
                        print "entity-limit = {0}".format(args[1])
                    else:
                        print "Invalid vale. Valid values are positive integers and zero"

            elif args[0] == "workload":
                
                if len(args) == 1:
                    number = 1
                    for w in self.world_list:
                        print "### world{0} ###".format(number)
                        number += 1
                        print w, "\n"
                    print "### regionset ###"
                    print self.regionset
                    print "(Use: \"set workload world1\" or name_of_the_world or regionset)"
                    print "\n"
                else:
                    a = args[1]
                    if len(a) == 6 and a[:5] == "world" and int(a[-1]) >= 1 :
                        # get the number and choos the correct world from the list
                        number = int(args[1][-1]) - 1
                        try:
                            self.current = self.world_list[number]
                            print "workload = {0}".format(self.current.world_path)
                        except IndexError:
                            print "This world is not in the list!"
                    elif a in self.world_names:
                        for w in self.world_list:
                            if w.name == args[1]:
                                self.current = w
                                print "workload = {0}".format(self.current.world_path)
                                break
                        else:
                            print "This world name is not on the list!"
                    elif args[1] == "regionset":
                        if len(self.regionset):
                            self.current = self.regionset
                        else:
                            print "The region set is empty!"
                    else:
                        print "Invalid value."

            elif args[0] == "processes":
                if len(args) == 1:
                    print "processes = {0}".format(self.options.processes)
                else:
                    if int(args[1]) > 0:
                        self.options.processes = int(args[1])
                        print "processes = {0}".format(args[1])
                    else:
                        print "Invalid value. Valid values are positive integers."

            elif args[0] == "verbose":
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
        if self.current and self.current.scanned:
            if len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg == "entities":
                    n = self.current.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                    print "Chunks with too much entities problem: {0}. (Note: entity limit = {1}).".format(n)
                elif arg == "corrupted":
                    n = self.current.count_chunks(world.CHUNK_CORRUPTED)
                    print "Corrupted chunks: {0}".format(n)
                elif arg == "wrong":
                    n = self.current.count_chunks(world.CHUNK_WRONG_LOCATED)
                    print "Wrong located chunks: {0}".format(n)
                elif arg == "all":
                    nw = self.current.count_chunks(world.CHUNK_WRONG_LOCATED)
                    nc = self.current.count_chunks(world.CHUNK_CORRUPTED)
                    ne = self.current.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                    
                    print "Corrupted chunks: {0}".format(nc)
                    print "Wrong located chunks: {0}".format(nw)
                    print "Chunks with too much entities problem: {0}. (Note: entity limit = {1}).".format(ne, self.options.entity_limit)
                    
                else:
                    print "Unknown counter."
        else:
            print "The world hasn't be scanned. Use \'scan\' to scan it."

    def do_list(self, arg):
        # TODO: this is completely broken 
        if len(arg.split()) > 1:
            print "Error: too many parameters."
        else:
            if arg == "corrupted":
                print summary(self.current, [world.CHUNK_CORRUPTED])
            elif arg == "wrong":
                print summary(self.current, [world.CHUNK_WRONG_LOCATED])
            elif arg == "entities":
                print summary(self.current, [world.CHUNK_TOO_MUCH_ENTITIES])
            else:
                print "Unknown list."

    def do_regionset(self, arg):
        if len(arg) == 0:
            if self.current: print self.current
            else: print "No world/region-set set! Use \'set workload\' to set a world/regionset to work with."
        else:
            print "This command doesn't use any arguments."

    def do_scan(self, arg):
        if len(arg.split()) > 0:
            print "Error: too many parameters."
        else:
            if self.current:
                scan_world(self.current, self.options)
            else:
                print "No world set! Use \'set workload\'"

    def do_remove_entities(self, arg):
        # TODO: once scanned you don't need scan it again to change the status of the chunks with too much entities, 
        # the number of entities is stored in the ScannedChunks obj. Make it in this way?
        # also, prompt a yes question?
        if self.current and self.current.scanned:
            print "WARNING: This will delete all the entities in the chunks that have more entities than entity-limit. Note: you need to rescan your world if you change entity-limit. Are you sure you want to continue?"
            if len(arg.split()) > 0:
                print "Error: too many parameters."
            else:
                counter = self.current.remove_entities()
                print "Deleted {0} entities.".format(counter)
        else:
            print "The world hasn't be scanned. Use \'scan\' to scan it."
            
            
    def do_remove_chunks(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg == "corrupted":
                    self.current.remove_problematic_chunks(world.CHUNK_CORRUPTED)
                elif arg == "wrong":
                    self.current.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
                elif arg == "entities":
                    # TODO: there should be a remove_entities command and this one should be remove chunks
                    # it'd be a good a idea to throw a big warning telling that you can delete the entities
                    # without deleting the chunks.
                    counter = self.current.remove_problematic_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                    print "Done! Removed {0} chunks".format(counter)
                elif arg == "all":
                    self.current.remove_problematic_chunks(world.CHUNK_CORRUPTED)
                    self.current.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
                    counter = self.current.remove_problematic_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                else:
                    print "Unknown argumen."
        else:
            print "The world hasn't be scanned. Use \'scan\' to scan it."

    def do_replace_chunks(self, arg):
        # TODO: parece que sustituye los chunks sin comprobar si están bien o no!
        # el replace necesita una buena revisión
        if self.current and self.current.scanned:
            if len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg == "corrupted":
                    if self.current.count_chunks(world.CHUNK_CORRUPTED):
                        counter = self.current.replace_problematic_chunks(self.backup_worlds, world.CHUNK_CORRUPTED, self.options)
                        print "Done! Replaced {0} chunks".format(counter)
                    else:
                        print "No corrupted chunks to replace!"
                elif arg == "wrong":
                    if self.current.count_chunks(world.CHUNK_WRONG_LOCATED):
                        counter = self.current.replace_problematic_chunks(self.backup_worlds, world.CHUNK_WRONG_LOCATED, self.options, )
                        print "Done! Replaced {0} chunks".format(counter)
                    else:
                        print "No wrong located chunks to replace!"
                elif arg == "entities":
                    if self.current.count_chunks(world.CHUNK_WRONG_LOCATED):
                        counter = self.current.replace_problematic_chunks(self.backup_worlds, world.CHUNK_TOO_MUCH_ENTITIES, self.options)
                        print "Done! Replaced {0} chunks".format(counter)
                    else:
                        print "No chunks with too much entities problems to replace!"
                elif arg == "all":
                    counter = self.current.replace_problematic_chunks(self.backup_worlds, world.CHUNK_CORRUPTED, self.options)
                    counter += self.current.replace_problematic_chunks(self.backup_worlds, world.CHUNK_WRONG_LOCATED, self.options)
                    counter += self.current.replace_problematic_chunks(self.backup_worlds, world.CHUNK_TOO_MUCH_ENTITIES, self.options)
                    print "Done! Replaced {0} chunks".format(counter)
                else:
                    print "Unknown argumen."
        else:
            print "The world hasn't be scanned. Use \'scan\' to scan it."
            
    def do_quit(self, arg):
        print "Quitting."
        return True

    def do_exit(self, arg):
        print "Exiting."
        return True

    def do_EOF(self, arg):
        print "Quitting."
        return True

    # complete
    # TODO: complete set
    def complete_arg(self, text, possible_args):
        l = []
        for arg in possible_args:
            if text in arg and arg.find(text) == 0:
                l.append(arg)
        return l

    def complete_set(self, text, line, begidx, endidx):
        #~ print text, line,
        possible_args = ('entity-limit','verbose','processes','workload')
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
    def help_regionset(self):
        print "Prints information of the current region-set/world. This will be the region-set/world to scan and fix."
    def help_scan(self):
        print "Scans the world set or the region set choosen when region-fixer is ran."
    def help_count(self):
        print "Prints out the number of chunks with that error. Example: \n\'count corrupted\'\n \
                prints the number of corrupted chunks in the world.\nProblems are: corrupted, wrong, entities or all"
    def help_remove_entities(self):
        print "Remove all the entities in chunks that have more than entity-limit entities."
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

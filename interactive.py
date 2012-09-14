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
from scan import scan_world, scan_regionset

class interactive_loop(Cmd):
    def __init__(self, world_list, regionset, options, backup_worlds):
        Cmd.__init__(self)
        self.world_list = world_list
        self.regionset = regionset
        self.world_names = [str(i.name)  for i in self.world_list]
        # if there's only one world use it 
        if len(self.world_list) == 1 and len(self.regionset) == 0:
            self.current = world_list[0]
        elif len(self.world_list) == 0 and len(self.regionset) > 0:
            self.current = self.regionset
        else:
            self.current = None
        self.options = options
        self.backup_worlds = backup_worlds
        self.prompt = "#-> "
        self.intro = "Minecraft Region-Fixer interactive mode.\n(Note: Use tab to autocomplete. Type help for a list of commands.)\n"
    
    # do
    def do_set(self,arg):
        """ Command to change some options and variables in interactive
            mode """
        args = arg.split()
        if len(args) > 2:
            print "Error: too many parameters."
        elif len(args) == 0:
            print "Write \'help set\' to see a list of all possible variables"
        else:
            if args[0] == "entity-limit":
                if len(args) == 1:
                    print "entity-limit = {0}".format(self.options.entity_limit)
                else:
                    try:
                        if int(args[1]) >= 0:
                            self.options.entity_limit = int(args[1])
                            print "entity-limit = {0}".format(args[1])
                        else:
                            print "Invalid value. Valid values are positive integers and zero"
                    except ValueError:
                        print "Invalid value. Valid values are positive integers and zero"

            elif args[0] == "workload":

                if len(args) == 1:
                    if self.current:
                        print "Current workload:\n{0}\n".format(self.current.__str__())
                    print "List of possible worlds and region-sets:"
                    number = 1
                    for w in self.world_list:
                        print "   ### world{0} ###".format(number)
                        number += 1
                        # add a tab and print
                        for i in w.__str__().split("\n"): print "\t" + i
                        print 
                    print "   ### regionset ###"
                    for i in self.regionset.__str__().split("\n"): print "\t" + i
                    print "\n(Use \"set workload world1\" or name_of_the_world or regionset to choose one)"

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
                            print "workload = set of region files"
                        else:
                            print "The region set is empty!"
                    else:
                        print "Invalid world number, world name or regionset."

            elif args[0] == "processes":
                if len(args) == 1:
                    print "processes = {0}".format(self.options.processes)
                else:
                    try:
                        if int(args[1]) > 0:
                            self.options.processes = int(args[1])
                            print "processes = {0}".format(args[1])
                        else:
                            print "Invalid value. Valid values are positive integers."
                    except ValueError:
                        print "Invalid value. Valid values are positive integers."

            elif args[0] == "verbose":
                if len(args) == 1:
                    print "verbose = {0}".format(str(self.options.verbose))
                else:
                    if args[1] == "True":
                        self.options.verbose = True
                        print "verbose = {0}".format(args[1])
                    elif args[1] == "False":
                        self.options.verbose = False
                        print "verbose = {0}".format(args[1])
                    else:
                        print "Invalid value. Valid values are True and False."
            else:
                print "Invalid argument! Write \'help set\' to see a list of valid variables."

    def do_count(self, arg):
        """ Counts the number of chunks with the given problem and
            prints the result """
        if self.current and self.current.scanned:
            
            if len(arg.split()) == 0:
                print "Possible counters are: corrupted, wrong, entities, all."
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in ('corrupted', 'all','wrong','entities'):
                    if arg in ('corrupted', 'all'):
                        n = self.current.count_chunks(world.CHUNK_CORRUPTED)
                        print "Corrupted: {0}".format(n)
                    if arg in ('wrong', 'all'):
                        n = self.current.count_chunks(world.CHUNK_WRONG_LOCATED)
                        print "Wrong located: {0}".format(n)
                    if arg in ('entities', 'all'):
                        n = self.current.count_chunks(world.CHUNK_TOO_MUCH_ENTITIES)
                        print "Too much entities: {0}  (entity limit = {1})".format(n, self.options.entity_limit)
                else:
                    print "Unknown counter."
        else:
            print "The workload hasn't be scanned. Use \'scan\' to scan it."

    def do_summary(self, arg):
        """ Prints a summary of all the problems found in the region
            files. """
        if len(arg) == 0:
            if self.current:
                if self.current.scanned:
                    text = self.current.summary()
                    if text: print text
                    else: print "No problems found!"
                else:
                    print "The workload hasn't be scanned. Use \'scan\' to scan it."
            else:
                print "No world/region-set is set! Use \'set workload\' to set a world/regionset to work with."
        else:
            print "This command doesn't use any arguments."

    def do_current_workload(self, arg):
        """ Prints the info of the current workload """
        if len(arg) == 0:
            if self.current: print self.current
            else: print "No world/region-set is set! Use \'set workload\' to set a world/regionset to work with."
        else:
            print "This command doesn't use any arguments."

    def do_scan(self, arg):
        """ Scans the current workload. """
        if len(arg.split()) > 0:
            print "Error: too many parameters."
        else:
            if self.current:
                if isinstance(self.current, world.World):
                    scan_world(self.current, self.options)
                elif isinstance(self.current, world.RegionSet):
                    print "\n{0:-^60}".format(' Scanning region files ')
                    scan_regionset(self.current, self.options)
            else:
                print "No world set! Use \'set workload\'"

    def do_remove_entities(self, arg):
        # TODO: once scanned you don't need scan it again to change the status of the chunks with too much entities, 
        # the number of entities is stored in the ScannedChunks obj. Make it in this way?
        if self.current and self.current.scanned:
            if len(arg.split()) > 0:
                print "Error: too many parameters."
            else:
                print "WARNING: This will delete all the entities in the chunks that have more entities than entity-limit, make sure you know what entities are!.\nNote: you need to rescan your world if you change entity-limit.\nAre you sure you want to continue? (yes/no):"
                answer = raw_input()
                if answer == 'yes':
                    counter = self.current.remove_entities()
                    print "Deleted {0} entities.".format(counter)
                elif answer == 'no':
                    print "Ok!"
                else: print "Invalid answer, use \'yes\' or \'no\' the next time!."
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
    def complete_arg(self, text, possible_args):
        l = []
        for arg in possible_args:
            if text in arg and arg.find(text) == 0:
                l.append(arg)
        return l

    def complete_set(self, text, line, begidx, endidx):
        if "workload " in line:
            # return the list of world names plus 'regionset' plus a list of world1, world2...
            possible_args = tuple(self.world_names) + ('regionset',) + tuple([ 'world' + str(i+1) for i in range(len(self.world_names))])
        elif 'verbose ' in line:
            possible_args = ('True','False')
        else:
            possible_args = ('entity-limit','verbose','processes','workload')
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
    # TODO sería una buena idea poner un artículo de ayuda de como usar el programa en un caso típico.
    def help_set(self):
        print "Sets some variables used for the scan in interactive mode. If you run this command without variable you can see the current state. You can set:"
        print "   verbose" 
        print "If True prints a line per scanned region file instead of showing a progress bar."
        print "\n   entity-limit"
        print "If a chunk has more than this number of entities it will be added to the list of chunks with too-much-entities problem."
        print "\n   processes"
        print "Number of cores used while scanning the world."
        print "\n   workload"
        print "If you input a few worlds you can choose wich one will be scanned using this command."
    def help_current_workload(self):
        print "Prints information of the current region-set/world. This will be the region-set/world to scan and fix."
    def help_scan(self):
        print "Scans the world set or the region set choosen when region-fixer is ran."
    def help_count(self):
        print "   Prints out the number of chunks with that error. For example "
        print "\'count corrupted\' prints the number of corrupted chunks in the world."
        print 
        print "Possible counters are: corrupted, wrong, entities or all"
    def help_remove_entities(self):
        print "Remove all the entities in chunks that have more than entity-limit entities."
    def help_remove_chunks(self):
        print "Removes bad chunks with the given problem. Problems are: corrupted, wrong, entities. Please, be careful, when used with the too much entities problem this will remove the chunks with too much entities problems, not the entities.\nUsage: \"remove_chunks c\"\nthis will remove the corrupted chunks"
    def help_replace_chunks(self):
        print "Replaces bad chunks with the given problem, using the backups directories. Problems are: corrupted, wrong, entities or all.\nUsage: \"replace_chunks corrupted\"\nthis will replace the corrupted chunks with the given backups"
    def help_summary(self):
        print "Prints a summary of all the problems found in region files."
    def help_quit(self):
        print "Quits interactive mode, exits region-fixer."
    def help_EOF(self):
        print "Quits interactive mode, exits region-fixer."
    def help_help(self):
        print "Prints help help."

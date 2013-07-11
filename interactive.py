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


# TODO needs big update!
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
        self.intro = "Minecraft Region-Fixer interactive mode.\n(Use tab to autocomplete. Autocomplete doens't work on Windows. Type help for a list of commands.)\n"

        # other region-fixer stuff

        # possible args for chunks stuff
        possible_args = ""
        first = True
        for i in world.CHUNK_PROBLEMS_ARGS.values() + ['all']:
            if not first:
                possible_args += ", "
            possible_args += i 
            first = False
        self.possible_chunk_args_text = possible_args
        
        # possible args for region stuff
        possible_args = ""
        first = True
        for i in world.REGION_PROBLEMS_ARGS.values() + ['all']:
            if not first:
                possible_args += ", "
            possible_args += i 
            first = False
        self.possible_region_args_text = possible_args
        
    
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
                            print "Updating chunk status..."
                            self.current.rescan_entities(self.options)
                        else:
                            print "Invalid value. Valid values are positive integers and zero"
                    except ValueError:
                        print "Invalid value. Valid values are positive integers and zero"

            elif args[0] == "workload":

                if len(args) == 1:
                    if self.current:
                        print "Current workload:\n{0}\n".format(self.current.__str__())
                    print "List of possible worlds and region-sets (determined by the command used to run region-fixer):"
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
                    print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."
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
        # TODO: what about scanning while deleting entities as done in non-interactive mode?
        # this would need an option to choose which of the two methods use
        """ Scans the current workload. """
        if len(arg.split()) > 0:
            print "Error: too many parameters."
        else:
            if self.current:
                if isinstance(self.current, world.World):
                    self.current = world.World(self.current.path)
                    scan_world(self.current, self.options)
                elif isinstance(self.current, world.RegionSet):
                    print "\n{0:-^60}".format(' Scanning region files ')
                    scan_regionset(self.current, self.options)
            else:
                print "No world set! Use \'set workload\'"

    def do_count_chunks(self, arg):
        """ Counts the number of chunks with the given problem and
            prints the result """
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible counters are: {0}".format(self.possible_chunk_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.CHUNK_PROBLEMS_ARGS.values() or arg == 'all':
                    total = self.current.count_chunks(None)
                    for problem, status_text, a in world.CHUNK_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.count_chunks(problem)
                            print "Chunks with status \'{0}\': {1}".format(status_text, n)
                    print "Total chunks: {0}".format(total)
                else:
                    print "Unknown counter."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_count_regions(self, arg):
        """ Counts the number of regions with the given problem and
            prints the result """
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible counters are: {0}".format(self.possible_region_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.REGION_PROBLEMS_ARGS.values() or arg == 'all':
                    total = self.current.count_regions(None)
                    for problem, status_text, a in world.REGION_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.count_regions(problem)
                            print "Regions with status \'{0}\': {1}".format(status_text, n)
                    print "Total regions: {0}".format(total)
                else:
                    print "Unknown counter."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_count_all(self, arg):
        """ Print all the counters for chunks and regions. """
        if self.current and self.current.scanned:
            if len(arg.split()) > 0:
                print "This command doesn't requiere any arguments"
            else:
                print "{0:#^60}".format("Chunk problems:")
                self.do_count_chunks('all')
                print "\n"
                print "{0:#^60}".format("Region problems:")
                self.do_count_regions('all')
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_remove_entities(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) > 0:
                print "Error: too many parameters."
            else:
                print "WARNING: This will delete all the entities in the chunks that have more entities than entity-limit, make sure you know what entities are!.\nAre you sure you want to continue? (yes/no):"
                answer = raw_input()
                if answer == 'yes':
                    counter = self.current.remove_entities()
                    print "Deleted {0} entities.".format(counter)
                    if counter:
                        self.current.scanned = False
                    self.current.rescan_entities(self.options)
                elif answer == 'no':
                    print "Ok!"
                else: print "Invalid answer, use \'yes\' or \'no\' the next time!."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_remove_chunks(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_chunk_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.CHUNK_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.CHUNK_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.remove_problematic_chunks(problem)
                            if n:
                                self.current.scanned = False
                            print "Removed {0} chunks with status \'{1}\'.\n".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_replace_chunks(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_chunk_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.CHUNK_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.CHUNK_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.replace_problematic_chunks(self.backup_worlds, problem, self.options)
                            if n:
                                self.current.scanned = False
                            print "\nReplaced {0} chunks with status \'{1}\'.".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_replace_regions(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_region_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.REGION_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.REGION_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.replace_problematic_regions(self.backup_worlds, problem, self.options)
                            if n:
                                self.current.scanned = False
                            print "\nReplaced {0} regions with status \'{1}\'.".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."
        
    def do_remove_regions(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_region_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.REGION_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.REGION_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.remove_problematic_regions(problem)
                            if n:
                                self.current.scanned = False
                            print "\nRemoved {0} regions with status \'{1}\'.".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."
        pass

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
                l.append(arg + " ")
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

    def complete_count_chunks(self, text, line, begidx, endidx):
        possible_args = world.CHUNK_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_remove_chunks(self, text, line, begidx, endidx):
        possible_args = world.CHUNK_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_replace_chunks(self, text, line, begidx, endidx):
        possible_args = world.CHUNK_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_count_regions(self, text, line, begidx, endidx):
        possible_args = world.REGION_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_remove_regions(self, text, line, begidx, endidx):
        possible_args = world.REGION_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_replace_regions(self, text, line, begidx, endidx):
        possible_args = world.REGION_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    # help
    # TODO sería una buena idea poner un artículo de ayuda de como usar el programa en un caso típico.
    # TODO: the help texts need a normalize
    def help_set(self):
        print "\nSets some variables used for the scan in interactive mode. If you run this command without an argument for a variable you can see the current state of the variable. You can set:"
        print "   verbose" 
        print "If True prints a line per scanned region file instead of showing a progress bar."
        print "\n   entity-limit"
        print "If a chunk has more than this number of entities it will be added to the list of chunks with too many entities problem."
        print "\n   processes"
        print "Number of cores used while scanning the world."
        print "\n   workload"
        print "If you input a few worlds you can choose wich one will be scanned using this command.\n"
    def help_current_workload(self):
        print "\nPrints information of the current region-set/world. This will be the region-set/world to scan and fix.\n"
    def help_scan(self):
        print "\nScans the current world set or the region set.\n"

    def help_count_chunks(self):
        print "\n   Prints out the number of chunks with the given status. For example"
        print "\'count corrupted\' prints the number of corrupted chunks in the world."
        print 
        print "Possible status are: {0}\n".format(self.possible_chunk_args_text)
    def help_remove_entities(self):
        print "\nRemove all the entities in chunks that have more than entity-limit entities."
        print 
        print "This chunks are the ones with status \'too many entities\'.\n"
    def help_remove_chunks(self):
        print "\nRemoves bad chunks with the given problem."
        print
        print "Please, be careful, when used with the status too-many-entities this will" 
        print "REMOVE THE CHUNKS with too many entities problems, not the entities."
        print "To remove only the entities see the command remove_entities."
        print
        print "For example \'remove_chunks corrupted\' this will remove corrupted chunks."
        print
        print "Possible status are: {0}\n".format(self.possible_chunk_args_text)
        print
    def help_replace_chunks(self):
        print "\nReplaces bad chunks with the given status using the backups directories."
        print
        print "Exampe: \"replace_chunks corrupted\""
        print
        print "this will replace the corrupted chunks with the given backups."
        print
        print "Possible status are: {0}\n".format(self.possible_chunk_args_text)
        print
        print "Note: after replacing any chunks you have to rescan the world.\n"

    def help_count_regions(self):
        print "\n   Prints out the number of regions with the given status. For example "
        print "\'count_regions too-small\' prints the number of region with \'too-small\' status."
        print 
        print "Possible status are: {0}\n".format(self.possible_region_args_text)
    def help_remove_regions(self):
        print "\nRemoves regions with the given status."
        print
        print "Example: \'remove_regions too-small\'"
        print
        print "this will remove the region files with status \'too-small\'."
        print
        print "Possible status are: {0}".format(self.possible_region_args_text)
        print
        print "Note: after removing any regions you have to rescan the world.\n"
    def help_replace_regions(self):
        print "\nReplaces regions with the given status."
        print
        print "Example: \"replace_regions too-small\""
        print
        print "this will try to replace the region files with status \'too-small\'"
        print "with the given backups."
        print
        print "Possible status are: {0}".format(self.possible_region_args_text)
        print
        print "Note: after replacing any regions you have to rescan the world.\n"

    def help_summary(self):
        print "\nPrints a summary of all the problems found in the current workload.\n"
    def help_quit(self):
        print "\nQuits interactive mode, exits region-fixer. Same as \'EOF\' and \'exit\' commands.\n"
    def help_EOF(self):
        print "\nQuits interactive mode, exits region-fixer. Same as \'quit\' and \'exit\' commands\n"
    def help_exit(self):
        print "\nQuits interactive mode, exits region-fixer. Same as \'quit\' and \'EOF\' commands\n"
    def help_help(self):
        print "Prints help help."

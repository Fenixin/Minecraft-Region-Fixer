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

import platform
from os.path import join, split, exists, isfile
import world

# stolen from minecraft overviewer 
# https://github.com/overviewer/Minecraft-Overviewer/
def is_bare_console():
    """Returns true if Overviewer is running in a bare console in
    Windows, that is, if overviewer wasn't started in a cmd.exe
    session.
    """
    if platform.system() == 'Windows':
        try:
            import ctypes
            GetConsoleProcessList = ctypes.windll.kernel32.GetConsoleProcessList
            num = GetConsoleProcessList(ctypes.byref(ctypes.c_int(0)), ctypes.c_int(1))
            if (num == 1):
                return True
                
        except Exception:
            pass
    return False

def entitle(text, level = 0):
    """ Put the text in a title with lot's of hashes everywhere. """
    t = ''
    if level == 0:
        t += "\n"
        t += "{0:#^60}\n".format('')
        t += "{0:#^60}\n".format(' ' + text + ' ')
        t += "{0:#^60}\n".format('')
    return t
        

def table(columns):
    """ Gets a list with lists in which each list is a column,
        returns a text string with a table. """

    def get_max_len(l):
        """ Takes a list and returns the length of the biggest
            element """
        m = 0
        for e in l:
            if len(str(e)) > m:
                m = len(e)
        return m

    text = ""
    # stores the size of the biggest element in that column
    ml = []
    # fill up ml
    for c in columns:
        m = 0
        t = get_max_len(c)
        if t > m:
            m = t
        ml.append(m)
    # get the total width of the table:
    ml_total = 0
    for i in range(len(ml)):
        ml_total += ml[i] + 2 # size of each word + 2 spaces
    ml_total += 1 + 2# +1 for the separator | and +2 for the borders
    text += "-"*ml_total + "\n"
    # all the columns have the same number of rows
    row = get_max_len(columns)
    for r in range(row):
        line = "|"
        # put all the elements in this row together with spaces
        for i in range(len(columns)):
            line += "{0: ^{width}}".format(columns[i][r],width = ml[i] + 2)
            # add a separator for the first column
            if i == 0:
                line += "|"

        text += line + "|" + "\n"
        if r == 0:
            text += "-"*ml_total + "\n"
    text += "-"*ml_total
    return text


def parse_chunk_list(chunk_list, world_obj):
    """ Generate a list of chunks to use with world.delete_chunk_list.

    It takes a list of global chunk coordinates and generates a list of
    tuples containing:

    (region fullpath, chunk X, chunk Z)

    """
    # this is not used right now
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

def parse_paths(args):
    """ Parse the list of args passed to region-fixer.py and returns a 
    RegionSet object with the list of regions and a list of World 
    objects. """
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
        world folders. Returns a list of World objects. """
    
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

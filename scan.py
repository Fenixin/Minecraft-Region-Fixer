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

import nbt.region as region
import nbt.nbt as nbt
from os.path import split
import progressbar
import multiprocessing
from multiprocessing import queues
import world
import time
import sys

class ScannedRegionFile():
    """ Stores all the info for a scanned region file """
    def __init__(self, filename, corrupted, wrong, entities_prob, chunks, time):
        self.filename = filename
        self.corrupted_chunks = corrupted
        self.wronglocated_chunks = wrong
        self.entities_prob = entities_prob
        self.chunks = chunks
        # time when the scan finished
        self.scan_time = time 

class FractionWidget(progressbar.ProgressBarWidget):
    """ Convenience class to use the progressbar.py """
    def __init__(self, sep=' / '):
        self.sep = sep
        
    def update(self, pbar):
        return '%2d%s%2d' % (pbar.currval, self.sep, pbar.maxval)


def scan_level(world_obj):
    """ At the moment only tries to read a level.dat file and print a
    warning if there are problems. """

    w = world_obj

    try:
        level_dat = nbt.NBTFile(filename = w.level_file)
        del level_dat

    except Exception, e:
        w.level_problems.append(e)


def scan_player(world_obj, player_file_path):
    """ At the moment only tries to read a .dat player file. It returns
    0 if it's ok and 1 if has some problem """

    w = world_obj
    nick = split(player_file_path)[1].split(".")[0]
    try:
        player_dat = nbt.NBTFile(filename = player_file_path)
        world_obj.player_status[nick] = w.OK
        del player_dat

    except Exception, e:
        w.player_status[nick] = e
        w.player_with_problems.append(nick)


def scan_all_players(world_obj):
    """ Scans all the players using the scan_player function. """

    for player in world_obj.player_files:
        scan_player(world_obj, player)


def scan_mcr_file(region_file_path):
    """ Scans a region file reporting problems.
    
    Takes a RegionFile obj and returns a list of corrupted 
    chunks where each element represents a corrupted chunk and
    is a tuple containing:

    (region file, (coord x, coord y), problem) 

    This function is used from scan_all_mca_files and uses a
    multiprocessing queue to return in real time info about the process.
    """

    delete_entities = scan_mcr_file.options.delete_entities
    entity_limit = scan_mcr_file.options.entity_limit
    region_file = region.RegionFile(region_file_path)
    w = scan_mcr_file.w
    chunks = 0
    problems = []
    corrupted = 0
    wrong = 0
    entities_prob = 0
    filename = split(region_file.filename)[1]
    try:
        for x in range(32):
            for z in range(32):
                chunk, status, error_msg = scan_chunk(region_file, x, z)
                if status == 0:
                    chunks += 1
                    total_entities = len(chunk['Level']['Entities'].tags)
                    # deleting entities is in here because to parse a chunk with thousands of wrong entities
                    # takes a long time, and once detected is better to fix it at once.
                    if total_entities >= entity_limit:
                        if delete_entities:
                            empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')
                            chunk['Level']['Entities'] = empty_tag_list
                            print "Deleted {0} entities in chunk ({1},{2}).".format(total_entities, x, z)
                            region_file.write_chunk(x, z, chunk)

                        else:
                            problems.append((region_file.filename,(x,z),w.TOO_MUCH_ENTITIES))
                            entities_prob += 1
                            print "[WARNING!]: The chunk ({0},{1}) in region file {2} has {3} entities, and this may be too much. This may be a problem!".format(x,z,split(region_file.filename)[1],total_entities)

                            # This stores all the entities in a file,
                            # comes handy sometimes.
                            #~ pretty_tree = chunk['Level']['Entities'].pretty_tree()
                            #~ name = "{2}.chunk.{0}.{1}.txt".format(x,z,split(region_file.filename)[1])
                            #~ archivo = open(name,'w')
                            #~ archivo.write(pretty_tree)

                elif status == -1:
                    chunks += 1
                    problems.append((region_file.filename,(x,z),w.CORRUPTED))
                    corrupted += 1
                elif status == -2:
                    chunks += 1
                    problems.append((region_file.filename,(x,z),w.WRONG_LOCATED))
                    wrong += 1
                # if None do nothing

                del chunk # unload chunk from memory

        del region_file

    except KeyboardInterrupt:
        print "\nInterrupted by user\n"
        sys.exit(1)

    scan_mcr_file.q.put((filename, corrupted, wrong, entities_prob, chunks))

    return problems


def add_problem(world_obj, region_file, chunk, problem):
    """ This function adds a problem to the mcr_problems dict. """

    w = world_obj
    if region_file in w.mcr_problems:
        if chunk in w.mcr_problems[region_file]:
            w.mcr_problems[region_file][chunk].append(problem)
        else:
            w.mcr_problems[region_file][chunk] = []
            w.mcr_problems[region_file][chunk].append(problem)
    else:
        w.mcr_problems[region_file] = {}
        w.mcr_problems[region_file][chunk] = []
        w.mcr_problems[region_file][chunk].append(problem)



def scan_chunk(region_file, x, z):
    """ Returns a tuple with (chunk, status_integer, error_text).
     Status integers are: 0 if exists and it's OK, -1 if it's corrupted,
     -2 if it the header coords doesn't match the coords stored in the
     chunk data (wrong located chunk) and 1 if it doesn't exist.

     The variable chunk can be None if there's no chunk to return."""

    try:
        chunk = region_file.get_chunk(x,z)
        if chunk:
            data_coords = world.get_chunk_data_coords(chunk)
            header_coords = world.get_global_chunk_coords(region_file.filename, x, z)
            if data_coords != header_coords:
                return (chunk, -2, "Mismatched coordinates.")

    except region.RegionHeaderError as e:
        error = "Region header error: " + e.msg
        return (None, -1, error)

    except region.ChunkDataError as e:
        error = "Chunk data error: " + e.msg
        return (None, -1, error)

    except region.ChunkHeaderError as e:
        error = "Chunk herader error: " + e.msg
        return (None, -1, error)

    if chunk != None:
        return (chunk, 0, "OK")

    return (None, 1, "The chunk doesn't exist")


def _mp_pool_init(world_obj,options,q):
    """ Function to initialize the multiprocessing in scan_all_mca_files.
    Is used to pass values to the child process. """

    scan_mcr_file.q = q
    scan_mcr_file.options = options
    scan_mcr_file.w = world_obj


def scan_all_mca_files(world_obj, options):
    """ This function scans all te region files from a world_object
    printing status info in the process.
    
    Takes a world object and the options object from region-fixer.py and
    fills up the mcr_problems dict. 
    
    The process always uses a multiprocessing pool but the single thread
    code is still stored just in case is needed. """

    w = world_obj
    total_regions = len(w.all_mca_files)
    total_chunks = 0
    corrupted_total = 0
    wrong_total = 0
    entities_total = 0

    # init progress bar
    if not options.verbose:
        pbar = progressbar.ProgressBar(
            widgets=['Scanning: ', FractionWidget(), ' ', progressbar.Percentage(), ' ', progressbar.Bar(left='[',right=']'), ' ', progressbar.ETA()],
            maxval=total_regions)

    if True:
    #~ if abs(options.processes) >= 1:
        # queue used by processes to pass finished stuff
        q = queues.SimpleQueue()
        pool = multiprocessing.Pool(processes=options.processes,
                initializer=_mp_pool_init,initargs=(w,options,q))

        if not options.verbose:
            pbar.start()
        
        # start the pool
        result = pool.map_async(scan_mcr_file, w.all_mca_files, max(1,total_regions//options.processes))

        # printing status
        counter = 0

        while not result.ready() or not q.empty():
            time.sleep(0.01)
            if not q.empty():
                filename, corrupted, wrong, entities_prob, num_chunks = q.get()
                corrupted_total += corrupted
                wrong_total += wrong
                total_chunks += num_chunks
                entities_total += entities_prob
                counter += 1
                if options.verbose:
                    stats = "(c: {0}, w: {1}, t: {2})".format( corrupted, wrong, num_chunks)
                    print "Scanned {0: <15} {1:.<40} {2}/{3}".format(filename, stats, counter, total_regions)
                else:
                    pbar.update(counter)

        if not options.verbose: pbar.finish()

        # extract results and fill in the world class
        w.num_chunks = total_chunks
        for region_problems in result.get():
            for prob in region_problems:
                filename, chunk, problem = prob
                add_problem(w, filename, chunk, problem)


    else: # single thread version, non used anymore, left here because
          # just-in-case
    ################## not used >>>>>>>>>>>>>>>>>>>
        counter = 0
        
        # init the progress bar
        if not options.verbose:
            pbar.start()
            
        for region_path in w.all_mca_files:
            
            # scan for errors
            filename, corrupted, wrong, total = scan_mcr_file(region_path, options.delete_entities, options.entity_limit)
            counter += 1
            
            # print status
            if options.verbose:
                stats = "(corrupted: {0}, wrong located: {1}, chunks: {2})".format( len(corrupted), len(wrong), total)
                print "Scanned {0: <15} {1:.<60} {2}/{3}".format(filename, stats, counter, total_regions)
            else:
                pbar.update(counter)

            total_chunks += total
        
        if not options.verbose:    
            pbar.finish()
    #<<<<<<<<<<<<<<<<< not used ###################



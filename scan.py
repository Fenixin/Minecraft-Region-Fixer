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
import traceback

class ChildProcessException(Exception):
    """Takes the child process traceback text and prints it as a 
    real traceback with asterisks everywhere."""
    def __init__(self, r):
        # Helps to see wich one is the child process traceback
        print "*"*10
        print "*** Printint the child's Traceback:"
        print "*** Exception:", r[0], r[1]
        for tb in r[2]:
            print "*"*10
            print "*** File {0}, line {1}, in {2} \n***   {3}".format(*tb)
        print "*"*10

class FractionWidget(progressbar.ProgressBarWidget):
    """ Convenience class to use the progressbar.py """
    def __init__(self, sep=' / '):
        self.sep = sep
        
    def update(self, pbar):
        return '%2d%s%2d' % (pbar.currval, self.sep, pbar.maxval)

def scan_world(world_obj, options):
    w = world_obj
    # scan the world dir
    print "Scanning directory..."

    if not w.scanned_level.path:
        print "Warning: No \'level.dat\' file found!"
    if not w.normal_region_files:
        print "Warning: No region files found in the \"region\" directory!"
    if not w.nether_region_files:
        print "Info: No nether dimension in the world directory."
    if not w.aether_region_files:
        print "Info: No end dimension in the world directory."
    if w.players:
        print "There are {0} region files and {1} player files in the world directory.".format(\
            len(w.normal_region_files) + len(w.nether_region_files) + len(w.aether_region_files), len(w.players))
    else:
        print "There are {0} region files in the world directory.".format(\
            len(w.normal_region_files) + len(w.nether_region_files) + len(w.aether_region_files))

    # check the level.dat file and the *.dat files in players directory
    print "\n{0:-^60}".format(' Checking level.dat ')

    if not w.scanned_level.path:
        print "[WARNING!] \'level.dat\' doesn't exist!"
    else:
        if w.scanned_level.readable == True:
            print "\'level.dat\' is readable"
        else:
            print "[WARNING!]: \'level.dat\' is corrupted with the following error/s:"
            print "\t {0}".format(w.scanned_level.status_text)

    print "\n{0:-^60}".format(' Checking player files ')

    if not w.players:
        print "Info: No player files to scan."
    else:
        scan_all_players(w)        
        all_ok = True
        for name in w.players:
            if w.players[name].readable == False:
                print "[WARNING]: Player file {0} has problems.\n\tError: {1}".format(w.players[name].filename, w.players[name].status_text)
                all_ok = False
        if all_ok:
            print "All player files are readable."

    # SCAN ALL THE CHUNKS!
    if len(w.normal_region_files) + len(w.nether_region_files) + len(w.aether_region_files) == 0:
        print "No region files to scan!"
    else:
        if w.normal_region_files.regions:
            print "\n{0:-^60}".format(' Scanning the overworld ')
            scan_regionset(w.normal_region_files, options)
        if w.nether_region_files.regions:
            print "\n{0:-^60}".format(' Scanning the nether ')
            scan_regionset(w.nether_region_files, options)
        if w.aether_region_files.regions:
            print "\n{0:-^60}".format(' Scanning the end ')
            scan_regionset(w.aether_region_files, options)

    w.scanned = True


def scan_player(scanned_dat_file):
    """ At the moment only tries to read a .dat player file. It returns
    0 if it's ok and 1 if has some problem """

    s = scanned_dat_file
    try:
        player_dat = nbt.NBTFile(filename = s.path)
        s.readable = True
    except Exception, e:
        s.readable = False
        s.status_text = e


def scan_all_players(world_obj):
    """ Scans all the players using the scan_player function. """

    for name in world_obj.players:
        scan_player(world_obj.players[name])


def scan_region_file(to_scan_region_file):
    """ Scans a region file and fills a ScannedRegionFile obj.
    """
    try:
        r = to_scan_region_file
        o = scan_region_file.options
        delete_entities = o.delete_entities
        entity_limit = o.entity_limit
        regionset = scan_region_file.regionset
        region_file = region.RegionFile(r.path)
        chunk_count = 0
        corrupted = 0
        wrong = 0
        entities_prob = 0
        filename = r.filename
        try:
            for x in range(32):
                for z in range(32):
                    chunk, c = scan_chunk(region_file, (x,z), o)
                    if c != None: # chunk not created
                        r.chunks[(x,z)] = c
                        chunk_count += 1
                    else: continue
                    if c[TUPLE_STATUS] == world.CHUNK_OK:
                        continue
                    elif c[TUPLE_STATUS] == world.CHUNK_TOO_MANY_ENTITIES:
                        # deleting entities is in here because parsing a chunk with thousands of wrong entities
                        # takes a long time, and once detected is better to fix it at once.
                        if delete_entities:
                            world.delete_entities(region_file, x, z)
                            print "Deleted {0} entities in chunk ({1},{2}) of the region file: {3}".format(c[TUPLE_NUM_ENTITIES], x, z, r.filename)
                            # entities removed, change chunk status to OK
                            r.chunks[(x,z)] = (0, world.CHUNK_OK)

                        else:
                            entities_prob += 1
                            # This stores all the entities in a file,
                            # comes handy sometimes.
                            #~ pretty_tree = chunk['Level']['Entities'].pretty_tree()
                            #~ name = "{2}.chunk.{0}.{1}.txt".format(x,z,split(region_file.filename)[1])
                            #~ archivo = open(name,'w')
                            #~ archivo.write(pretty_tree)

                    elif c[TUPLE_STATUS] == world.CHUNK_CORRUPTED:
                        corrupted += 1
                    elif c[TUPLE_STATUS] == world.CHUNK_WRONG_LOCATED:
                        wrong += 1

        except KeyboardInterrupt:
            print "\nInterrupted by user\n"
            # TODO this should't exit directly in the next verion...
            sys.exit(1)

        r.chunk_count = chunk_count
        r.corrupted_chunks = corrupted
        r.wrong_located_chunks = wrong
        r.entities_prob = entities_prob
        r.scan_time = time.time()
        scan_region_file.q.put((r, filename, corrupted, wrong, entities_prob, chunk_count))

        return

        # Fatal exceptions:
    except IOError, e:
        print "\nWARNING: I can't open the file {0} !\nThe error is \"{1}\".\nTypical causes are file blocked or problems in the file system.\n".format(filename,e)
        # TODO: This doesn't need to be fatal.
        scan_region_file.q.put((r, filename, None))
        return

    except:
        # anything else is a ChildProcessException
        except_type, except_class, tb = sys.exc_info()
        scan_region_file.q.put((except_type, except_class, traceback.extract_tb(tb)))
        return

def scan_chunk(region_file, coords, options):
    """ Takes a RegionFile obj and the local coordinatesof the chunk as
        inputs, then scans the chunk and returns all the data."""
    try:
        chunk = region_file.get_chunk(*coords)
        if chunk:
            data_coords = world.get_chunk_data_coords(chunk)
            global_coords = world.get_global_chunk_coords(region_file.filename, coords[0], coords[1])
            num_entities = len(chunk["Level"]["Entities"])
            if data_coords != global_coords:
                status = world.CHUNK_WRONG_LOCATED
                status_text = "Mismatched coordinates (wrong located chunk)."
                scan_time = time.time()
            elif num_entities > options.entity_limit:
                status = world.CHUNK_TOO_MANY_ENTITIES
                status_text = "The chunks has too many entities (it has {0}, and it's more than the limit {1})".format(num_entities, options.entity_limit)
                scan_time = time.time()
            else:
                status = world.CHUNK_OK
                status_text = "OK"
                scan_time = time.time()
        else:
            data_coords = None
            global_coords = world.get_global_chunk_coords(region_file.filename, coords[0], coords[1])    
            num_entities = None
            status = world.CHUNK_NOT_CREATED
            status_text = "The chunk doesn't exist"
            scan_time = time.time()

    except region.RegionHeaderError as e:
        error = "Region header error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time.time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(region_file.filename, coords[0], coords[1])
        num_entities = None

    except region.ChunkDataError as e:
        error = "Chunk data error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time.time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(region_file.filename, coords[0], coords[1])
        num_entities = None

    except region.ChunkHeaderError as e:
        error = "Chunk herader error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time.time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(region_file.filename, coords[0], coords[1])
        num_entities = None
    
    return chunk, (num_entities, status) if status != world.CHUNK_NOT_CREATED else None

#~ TUPLE_COORDS = 0
#~ TUPLE_DATA_COORDS = 0
#~ TUPLE_GLOBAL_COORDS = 2
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1

#~ def scan_and_fill_chunk(region_file, scanned_chunk_obj, options):
    #~ """ Takes a RegionFile obj and a ScannedChunk obj as inputs, 
        #~ scans the chunk, fills the ScannedChunk obj and returns the chunk
        #~ as a NBT object."""
#~ 
    #~ c = scanned_chunk_obj
    #~ chunk, region_file, c.h_coords, c.d_coords, c.g_coords, c.num_entities, c.status, c.status_text, c.scan_time, c.region_path = scan_chunk(region_file, c.h_coords, options)
    #~ return chunk

def _mp_pool_init(regionset,options,q):
    """ Function to initialize the multiprocessing in scan_all_mca_files.
    Is used to pass values to the child process. """
    scan_region_file.regionset = regionset
    scan_region_file.q = q
    scan_region_file.options = options


def scan_regionset(regionset, options):
    """ This function scans all te region files in a regionset object 
    and fills the ScannedRegionFile obj with the results
    """

    total_regions = len(regionset.regions)
    total_chunks = 0
    corrupted_total = 0
    wrong_total = 0
    entities_total = 0

    # init progress bar
    if not options.verbose:
        pbar = progressbar.ProgressBar(
            widgets=['Scanning: ', FractionWidget(), ' ', progressbar.Percentage(), ' ', progressbar.Bar(left='[',right=']'), ' ', progressbar.ETA()],
            maxval=total_regions)

    # queue used by processes to pass finished stuff
    q = queues.SimpleQueue()
    pool = multiprocessing.Pool(processes=options.processes,
            initializer=_mp_pool_init,initargs=(regionset,options,q))

    if not options.verbose:
        pbar.start()

    # start the pool
    # Note to self: every child process has his own memory space,
    # that means every obj recived by them will be a copy of the
    # main obj
    result = pool.map_async(scan_region_file, regionset.get_region_list(), max(1,total_regions//options.processes))

    # printing status
    counter = 0

    while not result.ready() or not q.empty():
        time.sleep(0.01)
        if not q.empty():
            r = q.get()
            if len(r) == 3:
                raise ChildProcessException(r)
            else:
                scanned_regionfile, filename, corrupted, wrong, entities_prob, num_chunks = r
                # the obj returned is a copy, overwrite it in regionset
                regionset[world.get_region_coords(filename)] = scanned_regionfile
                corrupted_total += corrupted
                wrong_total += wrong
                total_chunks += num_chunks
                entities_total += entities_prob
                counter += 1
                if options.verbose:
                    stats = "(c: {0}, w: {1}, tme: {2}, t: {3})".format( corrupted, wrong, entities_prob, num_chunks)
                    print "Scanned {0: <15} {1:.<40} {2}/{3}".format(filename, stats, counter, total_regions)
                else:
                    pbar.update(counter)

    if not options.verbose: pbar.finish()
    
    regionset.scanned = True

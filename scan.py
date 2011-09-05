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
#~ from optparse import OptionParser
from os.path import split, getsize
import progressbar
import multiprocessing
import world
import time

class FractionWidget(progressbar.ProgressBarWidget):
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
        w.level_problems["file"] = e

def scan_player(world_obj, player_file_path):
    """ At the moment only tries to read a .dat player file. it returns
    0 if it's ok and 1 if has some problem """
    nick = split(player_file_path)[1].split(".")[0]
    try:
        player_dat = nbt.NBTFile(filename = player_file_path)
        world_obj.players_status[nick] = "OK"
        del player_dat

    except Exception, e:
        w.players_problems[nick] = e
        w.player_problems.append(nick)
    
def scan_all_players(world_obj):
    """ Scans all the players using the player function """
    for player in world_obj.player_files:
        scan_player(world_obj, player)

def scan_mcr_file(region_file, delete_entities = False, entity_limit = 500):
    """ Takes a RegionFile obj and returns a list of corrupted 
    chunks where each element represents a corrupted chunk and
    contains a tuple:
     (region file, coord x, coord y) 
     and returns also the total number of chunks (including corrupted ones)
     """

    total_chunks = 0
    bad_chunks = []
    wrong_located_chunks = []
    try:
        for x in range(32):
            for z in range(32):
                #~ print "In chunk ({0},{1})".format(x,z)
                chunk = scan_chunk(region_file, x, z)
                if isinstance(chunk, nbt.TAG_Compound):
                    total_chunks += 1
                    total_entities = len(chunk['Level']['Entities'].tags)
                    # deleting entities is here because to parse a chunk with thousands of wrong entities
                    # takes a long time, and once detected is better to fix it at once.
                    if delete_entities == True and total_entities > entity_limit:
                        
                        #~ print len(chunk['Level']['Entities'].tags)
                        empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')

                        chunk['Level']['Entities'] = empty_tag_list
                        #~ print len(chunk['Level']['Entities'].tags)
                        print "Deleted {0} entities in chunk ({1},{2}).".format(total_entities, x, z)
                        region_file.write_chunk(x, z, chunk)
                    
                    elif total_entities > entity_limit:
                        print "[WARNING!]: The chunk ({0},{1}) in region file {2} has {3} entities, and this may be too much. This may be a problem!".format(x,z,region_file,total_entities)
                        
                elif chunk == -1:
                    total_chunks += 1
                    bad_chunks.append((region_file.filename,x,z))
                elif chunk == -2:
                    total_chunks += 1
                    wrong_located_chunks.append((region_file.filename,x,z))
                # if None do nothing
                del chunk # unload chunk from memory
                
        filename = split(region_file.filename)[1]

        del region_file
        
    except KeyboardInterrupt:
        print "\nInterrupted by user\n"
        sys.exit(1)
        
    return filename,bad_chunks, wrong_located_chunks, total_chunks

def _mp_scan_mcr_file(region_file):
    counter.value += 1
    if getsize(region_file) is not 0:
        r = scan_mcr_file(region.RegionFile(region_file),delete_entities,entity_limit)
        _mp_scan_mcr_file.q.put(r)
        return r
    else:
        return None

def scan_chunk(region_file, x, z):
    """ Returns the chunk if exists, -1 if it's corrupted, -2 if it the
    header coords doesn't match the coords storedn inside the chunk
     and None if it doesn't exist.
    """
    try:
        chunk = region_file.get_chunk(x,z)
        if chunk:
            data_coords = world.get_chunk_data_coords(chunk)
            header_coords = world.get_global_chunk_coords(region_file.filename, x, z)
            if data_coords != header_coords:
                return -2

    except region.RegionHeaderError:
        return -1
		
    except region.ChunkDataError:
        return -1

    except region.ChunkHeaderError:
        return -1
		
    return chunk

def scan_all_mcr_files(world_obj, options):

    w = world_obj
    total_chunks = 0
    corrupted_chunks = []
    wrong_located_chunks = []
    total_regions = len(w.all_mcr_files)
    counter_region = 0

    if not options.verbose:
        pbar = progressbar.ProgressBar(
            widgets=['Scanning: ', FractionWidget(), ' ', progressbar.Percentage(), ' ', progressbar.Bar(left='[',right=']'), ' ', progressbar.ETA()],
            maxval=total_regions)

    if abs(options.processes) > 1:
        #there is probably a better way to pass these values but this works for now
        q = multiprocessing.Queue()
        counter_region = multiprocessing.Value('d', 0) # TODO TODO Do we really need this?

        def _mp_pool_init(prog_counter,del_ents,ent_limit,q):
            _mp_scan_mcr_file.q = q
            global delete_entities
            delete_entities = del_ents
            global entity_limit
            entity_limit = ent_limit
            global counter
            counter = prog_counter

        pool = multiprocessing.Pool(processes=options.processes, initializer=_mp_pool_init,
            initargs=(counter_region,options.delete_entities,options.entity_limit,q))

        if not options.verbose:
            pbar.start()

        #the chunksize (arg #3) is pretty arbitrary, could probably be tweeked for better performance
        result = pool.map_async(_mp_scan_mcr_file, w.all_mcr_files, max(1,(total_regions//options.processes)//8))

        # printing status
        counter = 0
        while not result.ready() or (q.qsize() > 0 and options.verbose):
            #this loop should probably use result.wait(1) but i didn't want to take the time to figure out what wait() returns if it hits the timeout
            # TODO TODO TODO is really necessary result.wait(1)??
            time.sleep(0.5)
            if options.verbose:
                if q.qsize() > 0:
                    filename,corrupted, wrong, total = q.get()
                    counter += 1
                    stats = "(corrupted: {0}, wrong located: {1}, chunks: {2})".format( len(corrupted), len(wrong), total)
                    print "Scanned {0: <15} {1:.<60} {2}/{3}".format(filename, stats, counter, total_regions)
            else:
                pbar.update(counter)
        
        if not options.verbose: pbar.finish()
        
        # making the results redable for region-fixer
        for r in result.get():
            if r is not None:
                corrupted_chunks.extend(r[1])
                wrong_located_chunks.extend(r[2])
                total_chunks += r[3]

    else:
        counter = 0
        
        # init the progress bar
        if not options.verbose:
            pbar.start()
            
        for region_path in w.all_mcr_files:
            
            if getsize(region_path) != 0: # some region files are 0 bytes size! And minecraft seems to handle them without problem.
                region_file = region.RegionFile(region_path)
            else:
                continue
            
            # scan for errors
            filename, corrupted, wrong, total = scan_mcr_file(region_file, options.delete_entities, options.entity_limit)
            counter += 1
            
            # print status
            if options.verbose:
                stats = "(corrupted: {0}, wrong located: {1}, chunks: {2})".format( len(corrupted), len(wrong), total)
                print "Scanned {0: <15} {1:.<60} {2}/{3}".format(filename, stats, counter, total_regions)
            else:
                pbar.update(counter)

            corrupted_chunks.extend(corrupted)
            wrong_located_chunks.extend(wrong)

            total_chunks += total
        
        if not options.verbose:    
            pbar.finish()
    print "\nFound {0} corrupted and {1} wrong located chunks of a total of {2}\n".format(
        len(corrupted_chunks), len(wrong_located_chunks),total_chunks)


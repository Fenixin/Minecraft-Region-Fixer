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


from os.path import split, join
from time import sleep, time
import sys
import traceback
from copy import copy
import logging
import multiprocessing
from multiprocessing import queues

import nbt.region as region
import nbt.nbt as nbt

import progressbar
import world


#~ TUPLE_COORDS = 0
#~ TUPLE_DATA_COORDS = 0
#~ TUPLE_GLOBAL_COORDS = 2
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1


logging.basicConfig(filename='scan.log', level=logging.DEBUG)


class ChildProcessException(Exception):
    """Takes the child process traceback text and prints it as a
    real traceback with asterisks everywhere."""
    def __init__(self, error):
        # Helps to see wich one is the child process traceback
        traceback = error[2]
        print "*" * 10
        print "*** Error while scanning:"
        print "*** ", error[0]
        print "*" * 10
        print "*** Printing the child's Traceback:"
        print "*** Exception:", traceback[0], traceback[1]
        for tb in traceback[2]:
            print "*" * 10
            print "*** File {0}, line {1}, in {2} \n***   {3}".format(*tb)
        print "*" * 10


class FractionWidget(progressbar.ProgressBarWidget):
    """ Convenience class to use the progressbar.py """
    def __init__(self, sep=' / '):
        self.sep = sep

    def update(self, pbar):
        return '%2d%s%2d' % (pbar.currval, self.sep, pbar.maxval)


class AsyncRegionsetScanner(object):
    def __init__(self, regionset, processes, entity_limit,
                 remove_entities=False):

        self._regionset = regionset
        self.processes = processes
        self.entity_limit = entity_limit
        self.remove_entities = remove_entities

        # Queue used by processes to pass results
        self.queue = q = queues.SimpleQueue()
        self.pool = multiprocessing.Pool(processes=processes,
                initializer=_mp_pool_init,
                initargs=(regionset, entity_limit, remove_entities, q))

        # Recommended time to sleep between polls for results
        self.scan_wait_time = 0.001

    def scan(self):
        """ Scan and fill the given regionset. """
        total_regions = len(self._regionset.regions)
        self._results = self.pool.map_async(multithread_scan_regionfile,
                                            self._regionset.list_regions(None),
                                            max(1,total_regions//self.processes))
        # No more tasks to the pool, exit the processes once the tasks are done
        self.pool.close()

        # See method
        self._str_last_scanned = ""

    def get_last_result(self):
        """ Return results of last region file scanned.

        If there are left no scanned region files return None. The
        ScannedRegionFile returned is the same instance in the regionset,
        don't modify it or you will modify the regionset results.
        """

        q = self.queue
        logging.debug("AsyncRegionsetScanner: starting get_last_result")
        logging.debug("AsyncRegionsetScanner: queue empty: {0}".format(q.empty()))
        if not q.empty():
            logging.debug("AsyncRegionsetScanner: queue not empty")
            r = q.get()
            logging.debug("AsyncRegionsetScanner: result: {0}".format(r))
            if r is None:
                # Something went wrong scanning!
                raise ChildProcessException("Something went wrong \
                                        scanning a region-file.")
            # Overwrite it in the regionset
            if isinstance(r, tuple):
                raise ChildProcessException(r)
            self._regionset[r.get_coords()] = r
            self._str_last_scanned = self._regionset.get_name() + ": " + r.filename
            return r
        else:
            return None

    def terminate(self):
        """ Terminate the pool, this will exit no matter what.
        """
        self.pool.terminate()

    @property
    def str_last_scanned(self):
        """ A friendly string with last scanned thing. """
        return self._str_last_scanned if self._str_last_scanned else "Scanning..."

    @property
    def finished(self):
        """ Finished the operation. The queue could have elements """
        return self._results.ready() and self.queue.empty()

    @property
    def regionset(self):
        return self._regionset

    @property
    def results(self):
        """ Yield all the results from the scan.

        This is the preferred method to report scanning status. This way you
        can iterate through all the results in easy way:

        for result in scanner.results:
            # do things
        """

        q = self.queue
        logging.debug("AsyncRegionsetScanner: starting yield results")
        while not q.empty() or not self.finished:
            sleep(0.0001)
            logging.debug("AsyncRegionsetScanner: in while")
            if not q.empty():
                r = q.get()
                logging.debug("AsyncRegionsetScanner: result: {0}".format(r))
    #             if r is None:
    #                 # Something went wrong scanning!
    #                 raise ChildProcessException("Something went wrong \
    #                                         scanning a region-file.")
                # Overwrite it in the regionset
                self._regionset[r.get_coords()] = r
                yield r

    def __len__(self):
        return len(self._regionset)

class AsyncWorldScanner(object):
    def __init__(self, world_obj, processes, entity_limit,
                 remove_entities=False):

        self._world_obj = world_obj
        self.processes = processes
        self.entity_limit = entity_limit
        self.remove_entities = remove_entities

        self.regionsets = copy(world_obj.regionsets)

        self._current_regionset = None
        self._str_last_scanned = ""

        # Recommended time to sleep between polls for results
        self.scan_wait_time = 0.001

    def scan(self):
        """ Scan and fill the given regionset. """
        cr = AsyncRegionsetScanner(self.regionsets.pop(0),
                                   self.processes,
                                   self.entity_limit,
                                   self.remove_entities)
        self._current_regionset = cr
        cr.scan()

    def get_last_result(self):
        """ Return results of last region file scanned.

        If there are left no scanned region files return None. The
        ScannedRegionFile returned is the same instance in the regionset,
        don't modify it or you will modify the regionset results.

        This method is better if you want to closely control the scan
        process.
        """
        cr = self._current_regionset
        logging.debug("AsyncWorldScanner: current_regionset {0}".format(cr))
        if cr is not None:
            logging.debug("AsyncWorldScanner: cr.finished {0}".format(cr.finished))
            if not cr.finished:
                r = cr.get_last_result()
                self._str_last_scanned = cr.str_last_scanned
                return r
            elif self.regionsets:
                self.scan()
                return None
            else:
                return None
        else:
            return None

    def terminate(self):
        self._current_regionset.terminate()

    @property
    def str_last_scanned(self):
        """ A friendly string with last scanned thing. """
        return self._str_last_scanned

    @property
    def current_regionset(self):
        return self._current_regionset.regionset

    @property
    def finished(self):
        """ Finished the operation. The queue could have elements """
        return not self.regionsets and self._current_regionset.finished

    @property
    def world_obj(self):
        return self._world_obj

    @property
    def results(self):
        """ Yield all the results from the scan.

        This is the simpler method to control the scanning process,
        but also the most slopy. If you want to closely control the
        scan process (for example cancel the process in the middle,
        whatever is happening) use get_last_result().

        Example using this method:

        for result in scanner.results:
            # do things
        """

        while not self.finished:
            cr = self._current_regionset
            if cr and not cr.finished:
                for r in cr.results:
                    yield r
            elif self.regionsets:
                self.scan()

    def __len__(self):
        l = 0
        for rs in self.regionsets:
            l += len(rs)
        return l

class AsyncDataScanner(object):
    def __init__(self, data_dict, processes):

        self._data_dict = data_dict
        self.processes = processes

        self.queue = q = queues.SimpleQueue()
        self.pool = multiprocessing.Pool(processes=processes,
                initializer=_mp_player_pool_init,
                initargs=(q,))
        # Recommended time to sleep between polls for results
        self.scan_wait_time = 0.0001

    def scan(self):
        """ Scan and fill the given data_dict generated by world.py. """
        total_players = len(self._data_dict)
        player_list = self._data_dict.values()
        self._results = self.pool.map_async(multiprocess_scan_player,
                                            player_list,
                                            max(1, total_players//self.processes))
        # No more tasks to the pool, exit the processes once the tasks are done
        self.pool.close()

    def get_last_result(self):
        """ Return results of last player scanned. """

        q = self.queue
        logging.debug("AsyncDataScanner: starting get_last_result")
        logging.debug("AsyncDataScanner: queue empty: {0}".format(q.empty()))
        if not q.empty():
            logging.debug("AsyncDataScanner: queue not empty")
            p = q.get()
            logging.debug("AsyncDataScanner: result: {0}".format(p))
#             if p is None:
#                 # Something went wrong scanning!
#                 raise ChildProcessException("Something went wrong \
#                                         scanning a player-file.")
            # Overwrite it in the regionset
            self._data_dict[p.filename] = p
            return p
        else:
            return None

    @property
    def finished(self):
        """ Have the scan finished? """
        return self._results.ready() and self.queue.empty()

    @property
    def data_dict(self):
        return self._data_dict

    @property
    def results(self):
        """ Yield all the results from the scan.

        This is the preferred method to report scanning status. This way you
        can iterate through all the results in easy way:

        for result in scanner.results:
            # do things
        """

        q = self.queue
        logging.debug("AsyncDataScanner: starting yield results")
        logging.debug("AsyncDataScanner: queue empty: {0}".format(q.empty()))
        while not q.empty() or not self.finished:
            sleep(0.0001)
            logging.debug("AsyncDataScanner: in while")
            if not q.empty():
                p = q.get()
                logging.debug("AsyncDataScanner: result: {0}".format(p))
    #             if p is None:
    #                 # Something went wrong scanning!
    #                 raise ChildProcessException("Something went wrong \
    #                                         scanning a player-file.")
                # Overwrite it in the data dict
                self._data_dict[p.filename] = p
                yield p

    def __len__(self):
        return len(self._data_dict)

# All scanners will use this progress bar
widgets = ['Scanning: ',
           FractionWidget(),
           ' ',
           progressbar.Percentage(),
           ' ',
           progressbar.Bar(left='[', right=']'),
           ' ',
           progressbar.ETA()]


def console_scan_world(world_obj, processes, entity_limit, remove_entities):
    """ Scans a world folder including players and prints status to console.

    This functions uses AsyncDataScanner and AsyncWorldScanner.
    """

    # Time to wait beween asking for results. Note that if the time is too big
    # results will be waiting in the queue and the scan will take longer just
    # because of this.
    w = world_obj
    # Scan the world directory
    print "World info:"

    print ("There are {0} region files, {1} player files and {2} data"
           " files in the world directory.").format(
                                     w.get_number_regions(),
                                     len(w.players) + len(w.old_players),
                                     len(w.data_files))

    # check the level.dat
    print "\n{0:-^60}".format(' Checking level.dat ')

    if not w.scanned_level.path:
        print "[WARNING!] \'level.dat\' doesn't exist!"
    else:
        if w.scanned_level.readable == True:
            print "\'level.dat\' is readable"
        else:
            print "[WARNING!]: \'level.dat\' is corrupted with the following error/s:"
            print "\t {0}".format(w.scanned_level.status_text)

    ps = AsyncDataScanner(w.players, processes)
    ops = AsyncDataScanner(w.old_players, processes)
    ds = AsyncDataScanner(w.data_files, processes)
    ws = AsyncWorldScanner(w, processes, entity_limit, remove_entities)

    scanners = [ps, ops, ds, ws]

    scan_titles = [' Scanning UUID player files ',
                   ' Scanning old format player files ',
                   ' Scanning structures and map data files ',
                   ' Scanning region files ']
    try:
        for scanner, title in zip(scanners, scan_titles):
            # Scan player files
            print "\n{0:-^60}".format(title)
            if not len(scanner):
                print "Info: No files to scan."
            else:
                total = len(scanner)
                pbar = progressbar.ProgressBar(widgets=widgets, maxval=total)
                scanner.scan()
                counter = 0
                while not scanner.finished:
                    sleep(scanner.scan_wait_time)
                    result = scanner.get_last_result()
                    if result:
                        counter += 1
                    pbar.update(counter)
                pbar.finish()
        w.scanned = True
    except ChildProcessException, e:
        print "Something went really wrong scanning a region file."
        print "See a log for more details!"
        print e


def console_scan_regionset(regionset, processes, entity_limit,
                           remove_entities):
    """ Scan a regionset printing status to console.

    Uses AsyncRegionsetScanner.
    """

    total_regions = len(regionset)
    pbar = progressbar.ProgressBar(widgets=widgets,
                               maxval=total_regions)
    pbar.start()
    rs = AsyncRegionsetScanner(regionset, processes, entity_limit,
                               remove_entities)
    rs.scan()
    counter = 0
    while not rs.finished:
        sleep(0.01)
        result = rs.get_last_result()
        if result:
            counter += 1
            pbar.update(counter)

    pbar.finish()


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
    return s


def multiprocess_scan_player(player):
    """ Does the multithread stuff for scan_region_file """
    p = player
    p = scan_player(p)
    multiprocess_scan_player.q.put(p)


def _mp_player_pool_init(q):
    """ Function to initialize the multiprocessing in scan_regionset.
    Is used to pass values to the child process. """
    multiprocess_scan_player.q = q


def scan_all_players(world_obj):
    """ Scans all the players using the scan_player function. """

    for name in world_obj.players:
        scan_player(world_obj.players[name])


def scan_region_file(scanned_regionfile_obj, entity_limit, delete_entities):
    """ Given a scanned region file object with the information of a 
        region files scans it and returns the same obj filled with the
        results.

        If delete_entities is True it will delete entities while
        scanning

        entiti_limit is the threshold tof entities to conisder a chunk
        with too much entities problems.
    """

    try:
        r = scanned_regionfile_obj
        # counters of problems
        chunk_count = 0
        corrupted = 0
        wrong = 0
        entities_prob = 0
        shared = 0
        # used to detect chunks sharing headers
        offsets = {}
        filename = r.filename
        # try to open the file and see if we can parse the header
        try:
            region_file = region.RegionFile(r.path)
        except region.NoRegionHeader: # the region has no header
            r.status = world.REGION_TOO_SMALL
            return r
        except IOError, e:
            print "\nWARNING: I can't open the file {0} !\nThe error is \"{1}\".\nTypical causes are file blocked or problems in the file system.\n".format(filename,e)
            r.status = world.REGION_UNREADABLE
            r.scan_time = time()
            print "Note: this region file won't be scanned and won't be taken into acount in the summaries"
            # TODO count also this region files
            return r
        except: # whatever else print an error and ignore for the scan
                # not really sure if this is a good solution...
            print "\nWARNING: The region file \'{0}\' had an error and couldn't be parsed as region file!\nError:{1}\n".format(join(split(split(r.path)[0])[1], split(r.path)[1]),sys.exc_info()[0])
            print "Note: this region file won't be scanned and won't be taken into acount."
            print "Also, this may be a bug. Please, report it if you have the time.\n"
            return None

        try:# start the scanning of chunks
            
            for x in range(32):
                for z in range(32):

                    # start the actual chunk scanning
                    g_coords = r.get_global_chunk_coords(x, z)
                    chunk, c = scan_chunk(region_file, (x,z), g_coords, entity_limit)
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
            
            # Now check for chunks sharing offsets:
            # Please note! region.py will mark both overlapping chunks
            # as bad (the one stepping outside his territory and the
            # good one). Only wrong located chunk with a overlapping
            # flag are really BAD chunks! Use this criterion to 
            # discriminate
            metadata = region_file.metadata
            sharing = [k for k in metadata if (
                metadata[k].status == region.STATUS_CHUNK_OVERLAPPING and
                r[k][TUPLE_STATUS] == world.CHUNK_WRONG_LOCATED)]
            shared_counter = 0
            for k in sharing:
                r[k] = (r[k][TUPLE_NUM_ENTITIES], world.CHUNK_SHARED_OFFSET)
                shared_counter += 1

        except KeyboardInterrupt:
            print "\nInterrupted by user\n"
            # TODO this should't exit
            sys.exit(1)

        r.chunk_count = chunk_count
        r.corrupted_chunks = corrupted
        r.wrong_located_chunks = wrong
        r.entities_prob = entities_prob
        r.shared_offset = shared_counter
        r.scan_time = time()
        r.status = world.REGION_OK
        return r 

        # Fatal exceptions:
    except:
        # anything else is a ChildProcessException
        try:
            # Not even r was created, something went really wrong
            except_type, except_class, tb = sys.exc_info()
            r = (r.path, r.coords, (except_type, except_class, traceback.extract_tb(tb)))
        except NameError:
            r = (None, None, (except_type, except_class, traceback.extract_tb(tb)))
        
        return r


def scan_chunk(region_file, coords, global_coords, entity_limit):
    """ Takes a RegionFile obj and the local coordinatesof the chunk as
        inputs, then scans the chunk and returns all the data."""
    el = entity_limit
    try:
        chunk = region_file.get_chunk(*coords)
        data_coords = world.get_chunk_data_coords(chunk)
        num_entities = len(chunk["Level"]["Entities"])
        if data_coords != global_coords:
            status = world.CHUNK_WRONG_LOCATED
            status_text = "Mismatched coordinates (wrong located chunk)."
            scan_time = time()
        elif num_entities > el:
            status = world.CHUNK_TOO_MANY_ENTITIES
            status_text = "The chunks has too many entities (it has {0}, and it's more than the limit {1})".format(num_entities, entity_limit)
            scan_time = time()
        else:
            status = world.CHUNK_OK
            status_text = "OK"
            scan_time = time()

    except region.InconceivedChunk as e:
        chunk = None
        data_coords = None
        num_entities = None
        status = world.CHUNK_NOT_CREATED
        status_text = "The chunk doesn't exist"
        scan_time = time()

    except region.RegionHeaderError as e:
        error = "Region header error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except region.ChunkDataError as e:
        error = "Chunk data error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except region.ChunkHeaderError as e:
        error = "Chunk herader error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    return chunk, (num_entities, status) if status != world.CHUNK_NOT_CREATED else None


def _mp_pool_init(regionset, entity_limit, remove_entities, q):
    """ Function to initialize the multiprocessing in scan_regionset.
    Is used to pass values to the child process. """
    multithread_scan_regionfile.regionset = regionset
    multithread_scan_regionfile.q = q
    multithread_scan_regionfile.entity_limit = entity_limit
    multithread_scan_regionfile.remove_entities = remove_entities


def multithread_scan_regionfile(region_file):
    """ Does the multithread stuff for scan_region_file """
    r = region_file
    entity_limit = multithread_scan_regionfile.entity_limit
    remove_entities = multithread_scan_regionfile.remove_entities
    # call the normal scan_region_file with this parameters
    r = scan_region_file(r, entity_limit, remove_entities)

    # exceptions will be handled in scan_region_file which is in the
    # single thread land
    
    multithread_scan_regionfile.q.put(r)


if __name__ == '__main__':
    pass

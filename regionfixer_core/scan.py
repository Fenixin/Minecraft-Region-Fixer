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


import sys
import logging
import multiprocessing
from multiprocessing import SimpleQueue
from os.path import split, abspath
from time import sleep, time
from copy import copy
from traceback import extract_tb

import nbt.region as region
import nbt.nbt as nbt
from nbt.nbt import MalformedFileError
from nbt.region import ChunkDataError, ChunkHeaderError,\
                       RegionHeaderError, InconceivedChunk
from progressbar import ProgressBar, Bar, AdaptiveETA, SimpleProgress
from . import world

from regionfixer_core.util import entitle
from regionfixer_core.world import DATAFILE_OK


#~ TUPLE_COORDS = 0
#~ TUPLE_DATA_COORDS = 0
#~ TUPLE_GLOBAL_COORDS = 2
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1


logging.basicConfig(filename=None, level=logging.CRITICAL)


class ChildProcessException(Exception):
    """ Raised when a child process has problems.

    Stores all the info given by sys.exc_info() and the
    scanned file object which is probably partially filled.
    """
    def __init__(self, partial_scanned_file, exc_type, exc_class, tb_text):
        self.scanned_file = partial_scanned_file
        self.exc_type = exc_type
        self.exc_class = exc_class
        self.tb_text = tb_text

    @property
    def printable_traceback(self):
        """ Returns a nice printable traceback.

        It uses a lot of asteriks to ensure it doesn't mix with
        the main process traceback.
        """
        text = ""
        scanned_file = self.scanned_file
        text += "*" * 10 + "\n"
        text += "*** Exception while scanning:" + "\n"
        text += "*** " + str(scanned_file.filename) + "\n"
        text += "*" * 10 + "\n"
        text += "*** Printing the child's traceback:" + "\n"
        text += "*** Exception:" + str(self.exc_type) + str(self.exc_class) + "\n"
        for tb in self.tb_text:
            text += "*" * 10 + "\n"
            text += "*** File {0}, line {1}, in {2} \n***   {3}".format(*tb)
        text += "\n" + "*" * 10 + "\n"

        return text

    def save_error_log(self, filename='error.log'):
        """ Save the error in filename, return the absolute path of saved file. """
        f = open(filename, 'w')
        error_log_path = abspath(f.name)
        filename = self.scanned_file.filename
        f.write("Error while scanning: {0}\n".format(filename))
        f.write(self.printable_traceback)
        f.write('\n')
        f.close()

        return error_log_path


def multiprocess_scan_data(data):
    """ Does the multithread stuff for scan_data """
    # Protect everything so an exception will be returned from the worker
    try:
        result = scan_data(data)
        multiprocess_scan_data.q.put(result)
    except KeyboardInterrupt as e:
        raise e
    except:
        except_type, except_class, tb = sys.exc_info()
        s = (data, (except_type, except_class, extract_tb(tb)))
        multiprocess_scan_data.q.put(s)


def multiprocess_scan_regionfile(region_file):
    """ Does the multithread stuff for scan_region_file """
    # Protect everything so an exception will be returned from the worker
    try:
        r = region_file
        entity_limit = multiprocess_scan_regionfile.entity_limit
        remove_entities = multiprocess_scan_regionfile.remove_entities
        # call the normal scan_region_file with this parameters
        r = scan_region_file(r, entity_limit, remove_entities)
        multiprocess_scan_regionfile.q.put(r)
    except KeyboardInterrupt as e:
        raise e
    except:
        except_type, except_class, tb = sys.exc_info()
        s = (region_file, (except_type, except_class, extract_tb(tb)))
        multiprocess_scan_regionfile.q.put(s)


def _mp_data_pool_init(d):
    """ Function to initialize the multiprocessing in scan_regionset.
    Is used to pass values to the child process.

    Requiere to pass the multiprocessing queue as argument.
    """
    assert(type(d) == dict)
    assert('queue' in d)
    multiprocess_scan_data.q = d['queue']


def _mp_regionset_pool_init(d):
    """ Function to initialize the multiprocessing in scan_regionset.
    Is used to pass values to the child process. """
    assert(type(d) == dict)
    assert('regionset' in d)
    assert('queue' in d)
    assert('entity_limit' in d)
    assert('remove_entities' in d)
    multiprocess_scan_regionfile.regionset = d['regionset']
    multiprocess_scan_regionfile.q = d['queue']
    multiprocess_scan_regionfile.entity_limit = d['entity_limit']
    multiprocess_scan_regionfile.remove_entities = d['remove_entities']


class AsyncScanner(object):
    """ Class to derive all the scanner classes from.

    To implement a scanner you have to override:
    update_str_last_scanned()
    Use try-finally to call terminate, if not processes will be
    hanging in the background
     """
    def __init__(self, data_structure, processes, scan_function, init_args,
                 _mp_init_function):
        """ Init the scanner.

        data_structure is a world.DataSet
        processes is the number of child processes to use
        scan_function is the function to use for scanning
        init_args are the arguments passed to the init function
        _mp_init_function is the function used to init the child processes
        """
        assert(isinstance(data_structure, world.DataSet))
        self.data_structure = data_structure
        self.list_files_to_scan = data_structure._get_list()
        self.processes = processes
        self.scan_function = scan_function

        # Queue used by processes to pass results
        self.queue = SimpleQueue()
        init_args.update({'queue': self.queue})
        # NOTE TO SELF: initargs doesn't handle kwargs, only args!
        # Pass a dict with all the args
        self.pool = multiprocessing.Pool(processes=processes,
                initializer=_mp_init_function,
                initargs=(init_args,))

        # Recommended time to sleep between polls for results
        self.SCAN_START_SLEEP_TIME = 0.001
        self.SCAN_MIN_SLEEP_TIME = 1e-6
        self.SCAN_MAX_SLEEP_TIME = 0.1
        self.scan_sleep_time = self.SCAN_START_SLEEP_TIME
        self.queries_without_results = 0
        self.last_time = time()
        self.MIN_QUERY_NUM = 1
        self.MAX_QUERY_NUM = 5

        # Holds a friendly string with the name of the last file scanned
        self._str_last_scanned = None

    def scan(self):
        """ Launch the child processes and scan all the files. """
        
        logging.debug("########################################################")
        logging.debug("########################################################")
        logging.debug("Starting scan in: " + str(self))
        logging.debug("########################################################")
        logging.debug("########################################################")
        # Tests indicate that smaller amount of jobs per worker make all type
        # of scans faster
        jobs_per_worker = 5
        #jobs_per_worker = max(1, total_files // self.processes
        self._results = self.pool.map_async(self.scan_function,
                                            self.list_files_to_scan,
                                            jobs_per_worker)
                                            
        # No more tasks to the pool, exit the processes once the tasks are done
        self.pool.close()

        # See method
        self._str_last_scanned = ""

    def get_last_result(self):
        """ Return results of last file scanned. """

        q = self.queue
        ds = self.data_structure
        if not q.empty():
            d = q.get()
            if isinstance(d, tuple):
                self.raise_child_exception(d)
            # Copy it to the father process
            ds._replace_in_data_structure(d)
            ds._update_counts(d)
            self.update_str_last_scanned(d)
            # Got result! Reset it!
            self.queries_without_results = 0
            return d
        else:
            # Count amount of queries without result
            self.queries_without_results += 1
            return None

    def terminate(self):
        """ Terminate the pool, this will exit no matter what.
        """
        self.pool.terminate()

    def raise_child_exception(self, exception_tuple):
        """ Raises a ChildProcessException using the info
        contained in the tuple returned by the child process. """
        e = exception_tuple
        raise ChildProcessException(e[0], e[1][0], e[1][1], e[1][2])

    def update_str_last_scanned(self):
        """ Updates the string that represents the last file scanned. """
        raise NotImplemented

    def sleep(self):
        """ Sleep waiting for results.

        This method will sleep less when results arrive faster and
        more when they arrive slower.
        """
        # If the query number is outside of our range...
        if not ((self.queries_without_results < self.MAX_QUERY_NUM) &
                (self.queries_without_results > self.MIN_QUERY_NUM)):
            # ... increase or decrease it to optimize queries
            if (self.queries_without_results < self.MIN_QUERY_NUM):
                self.scan_sleep_time *= 0.5
            elif (self.queries_without_results > self.MAX_QUERY_NUM):
                self.scan_sleep_time *= 2.0
            # and don't go farther than max/min
            if self.scan_sleep_time > self.SCAN_MAX_SLEEP_TIME:
                logging.debug("Setting sleep time to MAX")
                self.scan_sleep_time = self.SCAN_MAX_SLEEP_TIME
            elif self.scan_sleep_time < self.SCAN_MIN_SLEEP_TIME:
                logging.debug("Setting sleep time to MIN")
                self.scan_sleep_time = self.SCAN_MIN_SLEEP_TIME

        # Log how it's going
        logging.debug("")
        logging.debug("Nº of queries without result: " + str(self.queries_without_results))
        logging.debug("Current sleep time: " + str(self.scan_sleep_time))
        logging.debug("Time between calls to sleep(): " + str(time() - self.last_time))
        self.last_time = time()

        # Sleep, let the other processes do their job
        sleep(self.scan_sleep_time)

    @property
    def str_last_scanned(self):
        """ A friendly string with last scanned thing. """
        return self._str_last_scanned if self._str_last_scanned \
            else "Scanning..."

    @property
    def finished(self):
        """ Finished the operation. The queue could have elements """
        return self._results.ready() and self.queue.empty()

    @property
    def results(self):
        """ Yield all the results from the scan.

        This is the simpler method to control the scanning process,
        but also the most sloppy. If you want to closely control the
        scan process (for example cancel the process in the middle,
        whatever is happening) use get_last_result().

        for result in scanner.results:
            # do things
        """

        q = self.queue
        T = self.SCAN_WAIT_TIME
        while not q.empty() or not self.finished:
            sleep(T)
            if not q.empty():
                d = q.get()
                if isinstance(d, tuple):
                    self.raise_child_exception(d)
                # Overwrite it in the data dict
                self.replace_in_data_structure(d)
                yield d

    def __len__(self):
        return len(self.data_structure)


class AsyncDataScanner(AsyncScanner):
    """ Scan a DataFileSet and fill the data structure. """
    def __init__(self, data_structure, processes):
        scan_function = multiprocess_scan_data
        init_args = {}
        _mp_init_function = _mp_data_pool_init

        AsyncScanner.__init__(self, data_structure, processes, scan_function,
                              init_args, _mp_init_function)

        # Recommended time to sleep between polls for results
        self.scan_wait_time = 0.0001

    def update_str_last_scanned(self, data):
        self._str_last_scanned = data.filename


class AsyncRegionsetScanner(AsyncScanner):
    """ Scan a RegionSet and fill the data structure. """
    def __init__(self, regionset, processes, entity_limit,
                 remove_entities=False):

        assert(isinstance(regionset, world.DataSet))

        scan_function = multiprocess_scan_regionfile
        _mp_init_function = _mp_regionset_pool_init

        init_args = {}
        init_args['regionset'] = regionset
        init_args['processes'] = processes
        init_args['entity_limit'] = entity_limit
        init_args['remove_entities'] = remove_entities

        AsyncScanner.__init__(self, regionset, processes, scan_function,
                              init_args, _mp_init_function)

        # Recommended time to sleep between polls for results
        self.scan_wait_time = 0.001

    def update_str_last_scanned(self, r):
        self._str_last_scanned = self.data_structure.get_name() + ": " + r.filename


class AsyncWorldRegionScanner(object):
    """ Wrapper around the calls of AsyncScanner to scan all the
    regionsets of a world. """
    def __init__(self, world_obj, processes, entity_limit,
                 remove_entities=False):

        self._world_obj = world_obj
        self.processes = processes
        self.entity_limit = entity_limit
        self.remove_entities = remove_entities

        self.regionsets = copy(world_obj.regionsets)

        self._current_regionset = None
        self._str_last_scanned = None

        # Holds a friendly string with the name of the last file scanned
        self.scan_wait_time = 0.001

    def sleep(self):
        """ Sleep waiting for results.

        This method will sleep less when results arrive faster and
        more when they arrive slower.
        """
        self._current_regionset.sleep()

    def scan(self):
        """ Scan and fill the given regionset. """
        cr = AsyncRegionsetScanner(self.regionsets.pop(0),
                                   self.processes,
                                   self.entity_limit,
                                   self.remove_entities)
        self._current_regionset = cr
        cr.scan()

        # See method
        self._str_last_scanned = ""

    def get_last_result(self):
        """ Return results of last region file scanned.

        If there are left no scanned region files return None. The
        ScannedRegionFile returned is the same instance in the regionset,
        don't modify it or you will modify the regionset results.

        This method is better if you want to closely control the scan
        process.
        """
        cr = self._current_regionset
        
        if cr is not None:
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
        but also the most sloppy. If you want to closely control the
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


def console_scan_loop(scanners, scan_titles, verbose):
    """ Uses all the AsyncScanner passed to scan the files and
    print status text to the terminal. """
    try:
        for scanner, title in zip(scanners, scan_titles):
            print("\n{0:-^60}".format(title))
            if not len(scanner):
                print("Info: No files to scan.")
            else:
                total = len(scanner)
                if not verbose:
                    pbar = ProgressBar(widgets=[SimpleProgress(), Bar(), AdaptiveETA()], maxval=total).start()
                try:
                    scanner.scan()
                    counter = 0
                    while not scanner.finished:
                        scanner.sleep()
                        result = scanner.get_last_result()
                        if result:
                            logging.debug("\nNew result: {0}\n\nOneliner: {1}\n".format(result,result.oneliner_status))
                            counter += 1
                            if not verbose:
                                pbar.update(counter)
                            else:
                                status = "(" + result.oneliner_status + ")"
                                fn = result.filename
                                print("Scanned {0: <12} {1:.<43} {2}/{3}".format(fn, status, counter, total))
                    if not verbose:
                        pbar.finish()
                except KeyboardInterrupt as e:
                    # If not, dead processes will accumulate in windows
                    scanner.terminate()
                    raise e
    except ChildProcessException as e:
#         print "\n\nSomething went really wrong scanning a file."
#         print ("This is probably a bug! If you have the time, please report "
#                "it to the region-fixer github or in the region fixer post "
#                "in minecraft forums")
#         print e.printable_traceback
        raise e


def console_scan_world(world_obj, processes, entity_limit, remove_entities,
                       verbose):
    """ Scans a world folder prints status to console.

    It will scan region files and data files (includes players).
    """

    # Time to wait between asking for results. Note that if the time is too big
    # results will be waiting in the queue and the scan will take longer just
    # because of this.
    w = world_obj
    # Scan the world directory
    print("World info:")

    print(("There are {0} region files, {1} player files and {2} data"
           " files in the world directory.").format(
                                     w.get_number_regions(),
                                     len(w.players) + len(w.old_players),
                                     len(w.data_files)))

    # check the level.dat
    print("\n{0:-^60}".format(' Checking level.dat '))

    if not w.scanned_level.path:
        print("[WARNING!] \'level.dat\' doesn't exist!")
    else:
        if w.scanned_level.status not in world.DATAFILE_PROBLEMS:
            print("\'level.dat\' is readable")
        else:
            print("[WARNING!]: \'level.dat\' is corrupted with the following error/s:")
            print("\t {0}".format(world.DATAFILE_STATUS_TEXT[w.scanned_level.status]))

    ps = AsyncDataScanner(w.players, processes)
    ops = AsyncDataScanner(w.old_players, processes)
    ds = AsyncDataScanner(w.data_files, processes)
    ws = AsyncWorldRegionScanner(w, processes, entity_limit, remove_entities)

    scanners = [ps, ops, ds, ws]

    scan_titles = [' Scanning UUID player files ',
                   ' Scanning old format player files ',
                   ' Scanning structures and map data files ',
                   ' Scanning region files ']
    console_scan_loop(scanners, scan_titles, verbose)
    w.scanned = True


def console_scan_regionset(regionset, processes, entity_limit,
                           remove_entities, verbose):
    """ Scan a regionset printing status to console.

    Uses AsyncRegionsetScanner.
    """

    rs = AsyncRegionsetScanner(regionset, processes, entity_limit,
                               remove_entities)
    scanners = [rs]
    titles = [entitle("Scanning separate region files", 0)]
    console_scan_loop(scanners, titles, verbose)
    regionset.scanned = True


def scan_data(scanned_dat_file):
    """ Try to parse the nbt data file, and fill the scanned object.

    If something is wrong it will return a tuple with useful info
    to debug the problem.

    NOTE: idcounts.dat (number of map files) is a nbt file and
    is not compressed, we handle the  special case here.

    """
    s = scanned_dat_file
    try:
        if s.filename == 'idcounts.dat':
            # TODO: This is ugly
            # Open the file and create a buffer, this way
            # NBT won't try to de-gzip the file
            f = open(s.path)

            _ = nbt.NBTFile(buffer=f)
        else:
            _ = nbt.NBTFile(filename=s.path)
        s.status = world.DATAFILE_OK
    except MalformedFileError as e:
        s.status = world.DATAFILE_UNREADABLE
    except IOError as e:
        s.status = world.DATAFILE_UNREADABLE
    except UnicodeDecodeError as e:
        s.status = world.DATAFILE_UNREADABLE
    except TypeError as e:
        s.status = world.DATAFILE_UNREADABLE
    
    except:
        s.status = world.DATAFILE_UNREADABLE
        except_type, except_class, tb = sys.exc_info()
        s = (s, (except_type, except_class, extract_tb(tb)))

    return s


def scan_region_file(scanned_regionfile_obj, entity_limit, delete_entities):
    """ Scan a region file filling the ScannedRegionFile

        If delete_entities is True it will delete entities while
        scanning

        entiti_limit is the threshold of entities to consider a chunk
        with too much entities problems.
    """
    try:
        r = scanned_regionfile_obj

        # try to open the file and see if we can parse the header
        try:
            region_file = region.RegionFile(r.path)
        except region.NoRegionHeader:  # The region has no header
            r.status = world.REGION_TOO_SMALL
            r.scan_time = time()
            r.scanned = True
            return r

        except PermissionError as e:
            r.status = world.REGION_UNREADABLE_PERMISSION_ERROR
            r.scan_time = time()
            r.scanned = True
            return r

        except IOError as e:
            r.status = world.REGION_UNREADABLE
            r.scan_time = time()
            r.scanned = True
            return r

        for x in range(32):
            for z in range(32):
                # start the actual chunk scanning
                g_coords = r.get_global_chunk_coords(x, z)
                chunk, c = scan_chunk(region_file,
                                      (x, z),
                                      g_coords,
                                      entity_limit)
                if c:
                    r[(x, z)] = c
                else:
                    # chunk not created
                    continue

                if c[TUPLE_STATUS] == world.CHUNK_OK:
                    continue
                elif c[TUPLE_STATUS] == world.CHUNK_TOO_MANY_ENTITIES:
                    # Deleting entities is in here because parsing a chunk
                    # with thousands of wrong entities takes a long time,
                    # and sometimes GiB of RAM, and once detected is better
                    # to fix it at once.
                    if delete_entities:
                        world.delete_entities(region_file, x, z)
                        print(("Deleted {0} entities in chunk"
                               " ({1},{2}) of the region file: {3}").format(
                                    c[TUPLE_NUM_ENTITIES], x, z, r.filename))
                        # entities removed, change chunk status to OK
                        r[(x, z)] = (0, world.CHUNK_OK)

                    else:
                        # This stores all the entities in a file,
                        # comes handy sometimes.
                        #~ pretty_tree = chunk['Level']['Entities'].pretty_tree()
                        #~ name = "{2}.chunk.{0}.{1}.txt".format(x,z,split(region_file.filename)[1])
                        #~ archivo = open(name,'w')
                        #~ archivo.write(pretty_tree)
                        pass
                elif c[TUPLE_STATUS] == world.CHUNK_CORRUPTED:
                    pass
                elif c[TUPLE_STATUS] == world.CHUNK_WRONG_LOCATED:
                    pass

        # Now check for chunks sharing offsets:
        # Please note! region.py will mark both overlapping chunks
        # as bad (the one stepping outside his territory and the
        # good one). Only wrong located chunk with a overlapping
        # flag are really BAD chunks! Use this criterion to
        # discriminate
        #
        # TODO: Why? I don't remember why
        # TODO: Leave this to nbt, which code is much better than this
         
        metadata = region_file.metadata
        sharing = [k for k in metadata if (
            metadata[k].status == region.STATUS_CHUNK_OVERLAPPING and
            r[k][TUPLE_STATUS] == world.CHUNK_WRONG_LOCATED)]
        shared_counter = 0
        for k in sharing:
            r[k] = (r[k][TUPLE_NUM_ENTITIES], world.CHUNK_SHARED_OFFSET)
            shared_counter += 1

        r.scan_time = time()
        r.status = world.REGION_OK
        r.scanned = True
        return r

    except KeyboardInterrupt:
        print("\nInterrupted by user\n")
        # TODO this should't exit. It should return to interactive
        # mode if we are in it.
        sys.exit(1)

        # Fatal exceptions:
    except:
        # Anything else is a ChildProcessException
        # NOTE TO SELF: do not try to return the traceback object directly!
        # A multiprocess pythonic hell comes to earth if you do so.
        except_type, except_class, tb = sys.exc_info()
        r = (scanned_regionfile_obj,
             (except_type, except_class, extract_tb(tb)))

        return r


def scan_chunk(region_file, coords, global_coords, entity_limit):
    """ Scans a chunk returning its status and number of entities.
    
    Keywords arguments:
    region_file -- nbt.RegionFile object
    coords -- tuple containing the local (region) coordinates of the chunk
    global_coords -- tuple containing the global (world) coordinates of the chunk
    entity_limit -- the number of entities that is considered to be too many
    
    Return:
    chunk -- as a nbt file
    (num_entities, status) -- tuple with the number of entities of the chunk and 
                              the status described by the CHUNK_* variables in 
                              world.py
    
    If the chunk does not exist (is not yet created it returns None
    """
    el = entity_limit
    try:
        chunk = region_file.get_chunk(*coords)
        data_coords = world.get_chunk_data_coords(chunk)
        num_entities = len(chunk["Level"]["Entities"])
        if data_coords != global_coords:
            # wrong located chunk
            status = world.CHUNK_WRONG_LOCATED
        elif num_entities > el:
            # too many entities in the chunk
            status = world.CHUNK_TOO_MANY_ENTITIES
        else:
            # chunk ok
            status = world.CHUNK_OK
    
    except InconceivedChunk as e:
        # chunk not created
        chunk = None
        data_coords = None
        num_entities = None
        status = world.CHUNK_NOT_CREATED

    except RegionHeaderError as e:
        # corrupted chunk, because of region header
        status = world.CHUNK_CORRUPTED
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except ChunkDataError as e:
        # corrupted chunk, usually because of bad CRC in compression
        status = world.CHUNK_CORRUPTED
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except ChunkHeaderError as e:
        # corrupted chunk, error in the header of the chunk
        status = world.CHUNK_CORRUPTED
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except KeyError as e:
        # chunk with the mandatory tag Entities missing
        status = world.CHUNK_MISSING_ENTITIES_TAG
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except UnicodeDecodeError as e:
        # TODO: This should another kind of error, it's now being handled as corrupted chunk
        status = world.CHUNK_CORRUPTED
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except TypeError as e:
        # TODO: This should another kind of error, it's now being handled as corrupted chunk
        status = world.CHUNK_CORRUPTED
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    return chunk, (num_entities, status) if status != world.CHUNK_NOT_CREATED else None


if __name__ == '__main__':
    pass

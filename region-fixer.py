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

from optparse import OptionParser, OptionGroup
from glob import glob
from os.path import join, split, exists, getsize
import sys
import nbt.region as region
import zlib
import gzip
import nbt.nbt as nbt
import progressbar
import multiprocessing
import time

class FractionWidget(progressbar.ProgressBarWidget):
    def __init__(self, sep=' / '):
        self.sep = sep
        
    def update(self, pbar):
        return '%2d%s%2d' % (pbar.currval, self.sep, pbar.maxval)

def parse_backup_list(world_backup_dirs):
    """ Generates a list with the input of backup dirs, also check if
    the backups dirs exists"""
    region_backup_dirs = []
    directories = world_backup_dirs.split(',')
    for dir in directories:
        region_dir = join(dir,"region")
        if exists(region_dir):
            region_backup_dirs.append(region_dir)
        else:
            print "[ATTENTION] The directory \"{0}\" is not a minecraft world directory".format(dir)
    return region_backup_dirs



def parse_chunk_list(chunk_list, region_dir):
    """ Fenerate a list of chunk as done by check_region_file
        but using a list of global chunk coords tuples as input"""
    parsed_list = []
    for chunk in chunk_list:
        region_name = get_chunk_region(chunk[0], chunk[1])
        fullpath = join(region_dir, region_name)
        parsed_list.append((fullpath, chunk[0], chunk[1]))

    return parsed_list
		

def check_region_file(region_file, delete_entities = False, entity_limit = 500):
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
                chunk = check_chunk(region_file, x, z)
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

def _mp_check_region_file(region_file):
    counter.value += 1
    if getsize(region_file) is not 0:
        r = check_region_file(region.RegionFile(region_file),delete_entities,entity_limit)
        _mp_check_region_file.q.put(r)
        return r
    else:
        return None

def check_chunk(region_file, x, z):
    """ Returns the chunk if exists, -1 if it's corrupted, -2 if it the
    header coords doesn't match the coords storedn inside the chunk
     and None if it doesn't exist.
    """
    try:
        chunk = region_file.get_chunk(x,z)
        if chunk:
            data_coords = get_chunk_data_coords(chunk)
            header_coords = get_global_chunk_coords(region_file.filename, x, z)
            if data_coords != header_coords:
                return -2

    except region.RegionHeaderError:
        return -1
		
    except region.ChunkDataError:
        return -1

    except region.ChunkHeaderError:
        return -1
		
    return chunk

def check_level_file(level_file):
    """ At the moment only tries to read a level.dat file and print a
    warning if there are problems. """
    try:
        level_dat = nbt.NBTFile(filename = level_file)
        print "\'level.dat\' is readable."
        del level_dat
        
    except Exception, e:
        print  "[WARNING!] The level.dat may be corrupted. Exception: \'{0}\'".format(e)

def check_player_file(player_file):
    """ At the moment only tries to read a .dat player file. it returns
    0 if it's ok and 1 if has some problem """
    try:
        player_dat = nbt.NBTFile(filename = player_file)
        del player_dat
        return 0
        
    except Exception, e:
        print  "[WARNING!] The player file {0} may be corrupted. Exception: \'{1}\'".format(player_file, e)
        return 1
    

def get_global_chunk_coords(region_filename, chunkX, chunkZ):
    """ Takes the region filename and the chunk local 
    coords and returns the global chunkcoords as integerss """
    
    regionX, regionZ = get_region_coords(region_filename)
    chunkX += regionX*32
    chunkZ += regionZ*32
    
    return chunkX, chunkZ

def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk coords """
    
    regionX = chunkX / 32
    regionZ = chunkZ / 32
    
    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mcr'
    
    return region_name
    

def get_region_coords(region_filename):
    """ Splits the region filename (full pathname or just filename)
        and returns his region coordinates.
        Return X and Z coords as integers. """
    
    splited = split(region_filename)
    filename = splited[1]
    list = filename.split('.')
    coordX = list[1]
    coordZ = list[2]
    
    return int(coordX), int(coordZ)
    
def get_chunk_data_coords(nbt_file):
    """ Gets the coords stored in the NBT structure of the chunk.
        Takes an nbt obj and returns the coords as integers.
        Don't confuse with get_global_chunk_coords! """
    
    level = nbt_file.__getitem__('Level')
            
    coordX = level.__getitem__('xPos').value
    coordZ = level.__getitem__('zPos').value
    
    return coordX, coordZ

def delete_chunk_list(list):
    """ Takes a list generated by check_region_file and deletes
    all the chunks on it and returns the number of deleted chunks"""
    
    region_file = region_path = None # variable inizializations
    
    counter = 0
    for chunk in list:
        x = chunk[1]
        z = chunk[2]
        
        region_path = chunk[0]
        region_file = region.RegionFile(region_path)
        region_file.unlink_chunk(x, z)
        counter += 1
        region_file.__del__
    
    return counter

def replace_chunk_list(list, backup_list):

    unfixed_list = []
    unfixed_list.extend(list)

    counter = 0

    for corrupted_chunk in list:
        x = corrupted_chunk[1]
        z = corrupted_chunk[2]

        print "\n{0:-^60}".format(' New chunk to fix! ')

        for backup in backup_list:
            Fixed = False
            region_file = split(corrupted_chunk[0])[1]

            # search for the region file
            backup_region_path = glob(join(backup, region_file))[0]
            region_file = corrupted_chunk[0]
            if backup_region_path:
                print "Backup region file found in: {0} \nfixing...".format(backup_region_path)

                # get the chunk
                backup_region_file = region.RegionFile(backup_region_path)
                working_chunk = check_chunk(backup_region_file, x, z)
                backup_region_file.__del__()
                
                if isinstance(working_chunk, nbt.TAG_Compound):
                    # the chunk exists and is non-corrupted, fix it!
                    tofix_region_file = region.RegionFile(region_file)
                    #~ print corrupted_chunk[1],corrupted_chunk[2],working_chunk
                    #~ print type(corrupted_chunk[1]),type(corrupted_chunk[2]),type(working_chunk)
                    tofix_region_file.write_chunk(corrupted_chunk[1], corrupted_chunk[2],working_chunk)
                    tofix_region_file.__del__
                    Fixed = True
                    counter += 1
                    unfixed_list.remove(corrupted_chunk)
                    print "Chunk fixed using backup dir: {0}".format(backup)
                    break
                    
                elif working_chunk == None:
                    print "The chunk doesn't exists in this backup directory: {0}".format(backup)
                    # The chunk doesn't exists in the region file
                    continue
                    
                elif working_chunk == -1:
                    # The chunk is corrupted
                    print "The chunk is corrupted in this backup directory: {0}".format(backup)
                    continue
                    
                elif working_chunk == -2:
                    # The chunk is corrupted
                    print "The chunk is wrong located in this backup directory: {0}".format(backup)
                    continue
    
    return unfixed_list, counter



def main():
    
    usage = 'usage: %prog [options] <world-path>'
    epilog = 'Copyright (C) 2011  Alejandro Aguilera (Fenixin) \
    https://github.com/Fenixin/Minecraft-Region-Fixer                                        \
    This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.txt. This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt for details.'

    parser = OptionParser(description='Script to check the integrity of a region file, \
                                            and to fix it, when posible, using with a backup of the map. \
                                            It uses NBT by twoolie the fork by MidnightLightning. \
                                            Written by Alejandro Aguilera (Fenixin). Sponsored by \
                                            NITRADO Servers (http://nitrado.net)',\
                                            prog = 'region-fixer', version='0.0.1', usage=usage, epilog=epilog)
    parser.add_option('--backups', '-b', metavar = '<backups>', type = str, dest = 'backups', help = 'List of backup directories of the Minecraft \
                                        world to use to fix corrupted chunks and/or wrong located chunks. Warning! This script is not going \
                                        to check if it \'s the same world, so be careful! \
                                        This argument can be a comma separated list (but never with spaces between elements!).', default = None)
    parser.add_option('--fix-corrupted','--fc', dest = 'fix_corrupted', action='store_true', \
                                            help = 'Tries to fix the corrupted chunks using the backups directories', default = False)
    parser.add_option('--fix-wrong-located','--fw', dest = 'fix_wrong_located', action='store_true', \
                                            help = 'Tries to fix the wrong located chunks using the backups directories', default = False)
    parser.add_option('--delete-corrupted', '--dc', action = 'store_true', help = '[WARNING!] This option deletes! And deleting can make you lose data, so be careful! :P \
                                            This option will delete all the corrupted chunks. Used with --fix-corrupted or --fix-wrong-located it will delete all the non-fixed chunks. \
                                            Minecraft will regenerate the chunk.', default = False)
    parser.add_option('--delete-wrong-located', '--dw', action = 'store_true', help = '[WARNING!] This option deletes! The same as --delete-corrupted but for \
                                            wrong located chunks', default = False)
                                            
    parser.add_option('--delete-entities', '--de', action = 'store_true', help = '[WARNING!] This option deletes! This deletes ALL the entities of chunks with more entities than --entity-limit (500 by default). In a Minecraft world entities are mobs and items dropped in the grond, items in chests and other stuff won\'t be touched. Read the README for more info. Region-Fixer will delete the entities when scanning so you can stop and resume the process', default = False, dest = 'delete_entities')
    parser.add_option('--entity-limit', '--el', action = 'store', type = int, help = 'Specify the limit for the --delete-entities option (default = 500).', dest = 'entity_limit', default = 500,)
    parser.add_option('--processes', '-p', action = 'store', type = int, help = 'Set the number of workers to use for scanning region files. Default is to not use multiprocessing at all', default = 1)
    parser.add_option('--verbose', '-v',action='store_true',help='Don\'t use progress bar, print a line per scanned region file.')
    
    # Other options
    other_group = OptionGroup(parser, "Others", "This option is a different part of the program and is incompatible with the options above.")
    
    other_group.add_option('--delete-list', metavar = '<delete_list>', type = str, help = 'This is a list of chunks to delete, the list must be a python list: \
                                            [(1,1), (-10,32)]. [INFO] if you use this option the world won\'t be scanned. Protect the parthesis from bash!', default = None)
    parser.add_option_group(other_group)
    (options, args) = parser.parse_args()

    # Only the world directory goes to args

    if not args:
        parser.error("No world path specified!")
        sys.exit()
    elif len(args) > 1:
        parser.error("Only one world dirctory needed!")
        sys.exit()

    world_path = args[0]
    if not exists(world_path):
        parser.error("The world path doesn't exists!")
        sys.exit()

    # Check basic options incompatibilities
    if options.backups and not (options.fix_corrupted or options.fix_wrong_located):
        parser.error("The option --backups needs one of the --fix-* options")
    
    if not options.backups and (options.fix_corrupted or options.fix_wrong_located):
        parser.error("The options --fix-* need the --backups option")

    print "Welcome to Region Fixer!"


    # do things with the option args
    level_dat_filename = join(world_path, "level.dat")
    player_files = glob(join(join(world_path, "players"), "*.dat"))

    backups = options.backups
    use_backups = False
    if backups: # create a list of directories containing the backup of the region files
        backup_dirs = parse_backup_list(backups)
        if not backup_dirs:
            print "[WARNING] No valid backup directories found, won't fix any chunk."
            fix_corrupted = fix_wrong_located = False

        else:
            use_backups = True


    world_region_dir = join(world_path,"region")
    if not exists(world_region_dir):
        print "Error: Doesn't look like a minecraft world directory!"
        sys.exit()

    world_nether_region_dir = join(world_path,"DIM-1/region")
    if not exists(world_nether_region_dir):
        print "Info: No nether dimension in the world directory."

    print "Scanning directory..."
    normal_region_files = glob(world_region_dir + "/r.*.*.mcr")
    nether_region_files = glob(world_nether_region_dir + "/r.*.*.mcr")

    if not normal_region_files and not nether_regioin_files:
        print "Error: No region files found!"
        sys.exit()

    if len(player_files) != 0:
        print "There are {0} region files and {1} player files in the world directory.".format(len(normal_region_files) + len(nether_region_files), len(player_files))
    else:
        print "There are {0} region files in the world directory.".format(len(normal_region_files) + len(nether_region_files))

    region_files = normal_region_files + nether_region_files

    # The program starts
    if options.delete_list: # Delete the given list of chunks
        try:
            delete_list = eval(options.delete_list)
        except:
            print 'Error: Wrong chunklist!'
            sys.exit()

        delete_list = parse_chunk_list(delete_list, world_region_dir)
        
        print "{0:#^60}".format(' Deleting the chunks on the list ')
        
        print "... ",
        
        counter = delete_chunk_list(delete_list)
        print "Done!"
        
        print "Deleted {0} chunks".format(counter)
        
    else:
        # check the level.dat file and the *.dat files in players directory

        print "\n{0:#^60}".format(' Scanning level.dat ')

        if not exists(level_dat_filename):
            print "[WARNING!] \'level.dat\' doesn't exist!"
        else:
            check_level_file(level_dat_filename)
        
        print "\n{0:#^60}".format(' Scanning player files ')
        
        problems = 0
        for player in player_files:
            problems += check_player_file(player)
        
        if not problems:
            print "All player files are readable."


        # check for corrupted chunks

        print "\n{0:#^60}".format(' Scanning region files ')

        total_chunks = 0
        corrupted_chunks = []
        wrong_located_chunks = []
        total_regions = len(region_files)
        counter_region = 0
        pbar = progressbar.ProgressBar(
            widgets=['Scanning: ', FractionWidget(), ' ', progressbar.Percentage(), ' ', progressbar.Bar(left='[',right=']'), ' ', progressbar.ETA()],
            maxval=total_regions)
        if abs(options.processes) > 1:
            #there is probably a better way to pass these values but this works for now
            q = multiprocessing.Queue()
            counter_region = multiprocessing.Value('d', 0)
            def _mp_pool_init(prog_counter,del_ents,ent_limit,q):
                _mp_check_region_file.q = q
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
            result = pool.map_async(_mp_check_region_file, region_files, max(1,(total_regions//options.processes)//8))
            
            # printing status
            counter = 0
            while not result.ready() or (q.qsize() > 0 and options.verbose):
                #this loop should probably use result.wait(1) but i didn't want to take the time to figure out what wait() returns if it hits the timeout
                time.sleep(0.5)
                if options.verbose:
                    if q.qsize() > 0:
                        filename,corrupted, wrong, total = q.get()
                        counter += 1
                        stats = "(corrupted: {0}, wrong located: {1}, chunks: {2})".format( len(corrupted), len(wrong), total)
                        print "Scanned {0: <15} {1:.<60} {2}/{3}".format(filename, stats, counter, total_regions)
                else:
                    pbar.update(counter_region.value)
            
            if not options.verbose: pbar.finish()
            
            # making the results redable for region-fixer
            for r in result.get():
                if r is not None:
                    corrupted_chunks.extend(r[1])
                    wrong_located_chunks.extend(r[2])
                    total_chunks += r[3]
        else:
            if options.verbose == False:
                pbar.start()
            for region_path in region_files:
                counter_region += 1
                if options.verbose:
                    print "Scanning {0}   ...  {1}/{2}".format(region_path, counter_region, total_regions)
                else:
                    pbar.update(counter_region)
                
                if getsize(region_path) != 0: # some region files are 0 bytes size! And minecraft seems to handle them without problem.
                    region_file = region.RegionFile(region_path)
                else:
                    continue
                filename, bad_list, wrong_list, chunks = check_region_file(region_file, options.delete_entities, options.entity_limit)
    
                corrupted_chunks.extend(bad_list)
                wrong_located_chunks.extend(wrong_list)
    
                total_chunks += chunks
            
            if not options.verbose:    
                pbar.finish()
        print "\nFound {0} corrupted and {1} wrong located chunks of a total of {2}\n".format(
            len(corrupted_chunks), len(wrong_located_chunks),total_chunks)


        # Try to fix corrupted chunks with the backup copy
        if use_backups and (corrupted_chunks or wrong_located_chunks):
            if options.fix_corrupted:
                print "{0:#^60}".format(' Trying to fix corrupted chunks ')
                unfixed_corrupted, counter = replace_chunk_list(corrupted_chunks, backup_dirs)
                print "\n{0} fixed chunks of a total of {1} corrupted chunks".format(counter, len(corrupted_chunks))
                corrupted_chunks = unfixed_corrupted # prepare the list for the deleting part
            
            if options.fix_wrong_located:
                print "{0:#^60}".format(' Trying to fix wrong located chunks ')
                unfixed_wrong_located, counter = replace_chunk_list(wrong_located_chunks, backup_dirs)
                print "\n{0} fixed chunks of a total of {1} wrong located chunks".format(counter, len(wrong_located_chunks))
                wrong_located_chunks = unfixed_wrong_located # prepare the list for the deleting part


        # delete bad chunks! (if asked for)
        if options.delete_corrupted and corrupted_chunks:
            
            print "{0:#^60}".format(' Deleting  corrupted chunks ')

            print "... ",
            counter = delete_chunk_list(corrupted_chunks)
            print "Done!"
            
            print "Deleted {0} corrupted chunks".format(counter)
        
        
        if options.delete_wrong_located and wrong_located_chunks:
            
            print "{0:#^60}".format(' Deleting wrong located chunks ')
            
            print "... ",
            counter = delete_chunk_list(wrong_located_chunks)
            print "Done!"
            
            print "Deleted {0} wrong located chunks".format(counter)


if __name__ == '__main__':
    main()

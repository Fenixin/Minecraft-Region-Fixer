======================
Minecraft Region Fixer
======================

By Alejandro Aguilera (Fenixin) 
Sponsored by NITRADO servers (http://nitrado.net)

Tries to fix Minecraft worlds (or region files).

Tries to fix corrupted chunks in region files using old backup copies
of the Minecraft world. If you don't have a copy, you can eliminate the
corrupted chunks.

Also it scans the 'level.dat' file and the player '*.dat' and tries to 
read them. If there are problems prints warnings. At the moment it
doesn't fix any problem in these files.

Web page:
https://github.com/Fenixin/Minecraft-Region-Fixer


Supported platforms
===================
This program seems to work with Python 2.7.x, and DOESN'T work with
python 3.x.

Usage
=====
You can read the program help running: “python region-fixer.py --help”

(NOTE: if you downloaded the .exe version for windows, use 
 "region-fixer.exe" instead of "python region-fixer.py")

Here are some examples:

This will scan your world and report any problems.

    $ python region-fixer.py /media/disk/corrupted-world/
    Welcome to Region Fixer!
    Scanning directory...
    There are 10 region files and 5 player files in the world directory.

    #################### Scanning level.dat ####################
    'level.dat'\ is redable

    ################## Scanning player files ###################
    All player files are readable.

    ################## Scanning region files ###################
    Scanning: 10 / 10 100% [############################] Time: 00:00:02

    Found 0 corrupted and 0 wrong located chunks of a total of 3368


You can use --verbose or -v option if you want more info:

    $ python region-fixer.py --verbose /media/disk/corrupted-world/
    Welcome to Region Fixer!
    Scanning directory...
    There are 10 region files and 5 player files in the world directory.

    #################### Scanning level.dat ####################
    'level.dat'\ is redable

    ################## Scanning player files ###################
    All player files are readable.

    ################## Scanning region files ###################
    Scanned r.-1.-2.mcr     (c: 0, w: 0, t: 3).................... 1/10
    Scanned r.0.-2.mcr      (c: 0, w: 0, t: 45)................... 2/10
    Scanned r.-1.0.mcr      (c: 0, w: 0, t: 214).................. 3/10
    Scanned r.-1.-1.mcr     (c: 0, w: 0, t: 125).................. 4/10
    Scanned r.-1.-1.mcr     (c: 0, w: 0, t: 449).................. 5/10
    Scanned r.-1.0.mcr      (c: 0, w: 0, t: 574).................. 6/10
    Scanned r.0.0.mcr       (c: 0, w: 0, t: 259).................. 7/10
    Scanned r.0.-1.mcr      (c: 0, w: 0, t: 149).................. 8/10
    Scanned r.0.-1.mcr      (c: 0, w: 0, t: 777).................. 9/10
    Scanned r.0.0.mcr       (c: 0, w: 0, t: 773).................. 10/10

    Found 0 corrupted and 0 wrong located chunks of a total of 3368


If we use the option "--delete-corrupted" or "--dc":

    $ python region-fixer.py --delete-corrupted /media/disk/corrupted-world/
    Welcome to Region Fixer!
    Scanning directory...
    There are 4 region files found on the world directory.

    ############## Scanning for corrupted chunks ###############
    Scanning /media/disk/corrupted-world/region/r.-1.0.mcr   ...  1/4
    Scanning /media/disk/corrupted-world/region/r.-1.-1.mcr   ...  2/4
    Scanning /media/disk/corrupted-world/region/r.0.0.mcr   ...  3/4
    Scanning /media/disk/corrupted-world/region/r.0.-1.mcr   ...  4/4

    Found 58 corrupted and 0 wrong located chunks of a total of 466

    ################ Deleting  corrupted chunks ################
    ...  Done!
    Deleted 58 corrupted chunks


If we make a backup every day of our world we can use them to fix 
the corrupted chunks, this method can spam a lot of output text, because
writes a log for every chunk that is trying to fix:

    $ python region-fixer.py --fix-corrupted --backups=/media/backups/2012-12-12/,/media/backups/2012-12-11/ /media/disk/corrupted-world/
    Welcome to Region Fixer!
    Scanning directory...
    There are 4 region files found on the world directory.

    ############## Scanning for corrupted chunks ###############
    Scanning /media/disk/corrupted-world/region/r.-1.0.mcr   ...  1/4
    Scanning /media/disk/corrupted-world/region/r.-1.-1.mcr   ...  2/4
    Scanning /media/disk/corrupted-world/region/r.0.0.mcr   ...  3/4
    Scanning /media/disk/corrupted-world/region/r.0.-1.mcr   ...  4/4

    Found 58 corrupted and 0 wrong located chunks of a total of 466

    ############## Trying to fix corrupted chunks ##############

    -------------------- New chunk to fix! ---------------------
    Backup region file found in: /media/disk/corrupted-world/region/r.-1.0.mcr 
    fixing...
    Chunk fixed using backup dir: /media/backups/2012-12-12/region

    -------------------- New chunk to fix! ---------------------
    Backup region file found in: /media/disk/corrupted-world/region/r.-1.0.mcr 
    fixing...
    Chunk fixed using backup dir: /media/backups/2012-12-12/region

    -------------------- New chunk to fix! ---------------------
    Backup region file found in: /media/disk/corrupted-world/region/r.-1.-1.mcr 
    fixing...
    Chunk fixed using backup dir: /media/backups/2012-12-12/region

        ...

    -------------------- New chunk to fix! ---------------------
    Backup region file found in: /media/disk/corrupted-world/region/r.-1.-1.mcr 
    fixing...
    Chunk fixed using backup dir: /media/backups/2012-12-12/region

    -------------------- New chunk to fix! ---------------------
    Backup region file found in: /media/disk/corrupted-world/region/r.0.-1.mcr 
    fixing...
    The chunk doesn't exists in this backup directory: /media/backups/2012-12-12/region

    -------------------- New chunk to fix! ---------------------
    Backup region file found in: /media/disk/corrupted-world/region/r.0.-1.mcr 
    fixing...
    The chunk doesn't exists in this backup directory: /media/backups/2012-12-11/region

This options have an equivalent for wrong located chunks.

Another problem that Region Fixer can fix is an entity problem.
Sometimes worlds store thousands of entities in one chunk, hanging the
server when loaded. This can happen with squids, spiders, or even items.
(experience orbs for example). Using the option "--delete-entities"
Region Fixer will delete all the entities in that chunk if it does have
more entities than entity-limit (see the help). It doesn't touch
TileEntities (chests, singposts, noteblocks, etc...). At the moment of
writing this Entities are:

- mobs
- items on the ground (don't worry chests are safe)
- vehicles (boats and minecarts)
- dynamic tiles (falling sand and activated TNT)

Note that you still need to load the chunk in Region Fixer to fix it, 
and it may need GIGs of RAM and lot of time. You can use this in
combination with "--entity-limit" to set your limit (default 500
entities).

    $python region-fixer.py --delete-entities --entity-limit=100 /media/disk/corrupted-world/
    Welcome to Region Fixer!
    Scanning directory...
    There are 4 region files found on the world directory.

    ############## Scanning for corrupted chunks ###############
    Scanning /media/disk/corrupted-world/region/r.-1.0.mcr   ...  1/4
    Scanning /media/disk/corrupted-world/region/r.-1.-1.mcr   ...  2/4
    Deleted 159 entities in chunk (21,8).
    Deleted 223 entities in chunk (22,16).
    Scanning /media/disk/corrupted-world/region/r.0.0.mcr   ...  3/4
    Scanning /media/disk/corrupted-world/region/r.0.-1.mcr   ...  4/4

    Found 2 corrupted and 0 wrong located chunks of a total of 466

For more info: “python region-fixer.py --help”


Warning
=======

This program has been tested with a lot of worlds, but the bugs always
appear, so please, MAKE A BACKUP OF YOUR WORLD BEFORE RUNNING THIS,
I'M NOT RESPONSIBLE OF WHAT HAPPENS TO YOUR WORLD. Think that you are
playing with you precious saved games :P .

Good luck! :)

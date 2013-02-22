======================
Minecraft Region Fixer
======================

By Alejandro Aguilera (Fenixin) 
Sponsored by NITRADO servers (http://nitrado.net)

Locates problems and tries to fix Minecraft worlds (or region files).

Tries to fix corrupted chunks in region files using old backup copies
of the Minecraft world. If you don't have a copy, you can eliminate the
corrupted chunks making Minecraft recreate them.

It also scans the 'level.dat' file and the player '\*.dat' and tries to 
read them. If there are any problems it prints warnings. At the moment
it doesn't fix any problem in these files.

Web page:
https://github.com/Fenixin/Minecraft-Region-Fixer


Supported platforms
===================
This program seems to work with Python 2.7.x, and DOESN'T work with
python 3.x. There is also a windows executable for ease of use, if you
use the windows executable you don't need to install Python.


Windows .exe downloads
======================
The window executable is generated using py2exe and is the choice if 
you don't want to install python in your system.

These downloads were usually in the downloads section of github, but 
github has deprecated this feature. So, from Region Fixer v0.1.0 
downloads are stored in mediafire:

http://www.mediafire.com/?1exub0d8ys83y
or
http://adf.ly/HVHGu   (if you want to contribute a little)


Notes
=====
Older versions of Minecraft had big problems when loading corrupted 
chunks. But in the latest versions of Minecraft (tested in 1.4.7) the
server itself removes corrupted chunks (when loading them) and 
regenerate those chunks. Region-Fixer still is useful for replacing 
those chunks with a backup, removing entities, or trying to see what's 
going wrong with your world.


Usage
=====
You can read the program help running: “python region-fixer.py --help”

(NOTE: if you downloaded the .exe version for windows, use 
 "region-fixer.exe" instead of "python region-fixer.py")

Here are some examples:

From v0.1.0 Region-Fixer can scan single region files and arbitrary 
region sets. For example, if you know where the problem is you could 
scan a single region file instead of scanning the whole world. You 
can also scan a few region files from different locations. Example::

    $ python region-fixer.py ~/.minecraft/saves/World1/region/r.0.0.mca 

    Welcome to Region Fixer!

    ############################################################
    ############## Scanning separate region files ##############
    ############################################################
    Scanning:  1 /  1 100% [########################################] Time: 00:00:01

    Found 0 corrupted, 0 wrong located chunks and 0 chunks with too many entities of a total of 976

The next example will scan your world and report any problems::

    $ python region-fixer.py ~/.minecraft/saves/corrupted-world

    Welcome to Region Fixer!

    ############################################################
    ############ Scanning world: Testing corruption ############
    ############################################################
    Scanning directory...
    Info: No nether dimension in the world directory.
    Info: No end dimension in the world directory.
    There are 1 region files and 1 player files in the world directory.

    -------------------- Checking level.dat --------------------
    'level.dat' is redable

    ------------------ Checking player files -------------------
    All player files are readable.

    ------------------ Scanning the overworld ------------------
    Scanning:  1 /  1 100% [########################################] Time: 00:00:20

    Found 19 corrupted, 0 wrong located chunks and 0 chunks with too many entities of a total of 625

You can use --verbose or -v option if you want more info. This option 
will print a line per region file showing problems found in that region 
file.

To delete corrupted chunks you can use "--delete-corrupted" or "--dc"::

    $ python region-fixer.py --delete-corrupted ~/.minecraft/saves/corrupted-world

    Welcome to Region Fixer!

    ############################################################
    ############ Scanning world: Testing corruption ############
    ############################################################
    Scanning directory...
    Info: No nether dimension in the world directory.
    Info: No end dimension in the world directory.
    There are 1 region files and 1 player files in the world directory.

    -------------------- Checking level.dat --------------------
    'level.dat' is redable

    ------------------ Checking player files -------------------
    All player files are readable.

    ------------------ Scanning the overworld ------------------
    Scanning:  1 /  1 100% [########################################] Time: 00:00:19

    Found 19 corrupted, 0 wrong located chunks and 0 chunks with too many entities of a total of 625

    ################ Deleting  corrupted chunks ################
     Deleting chunks in region set "/home/alejandro/.minecraft/saves/corrupted-world/region/": Done! Removed 19 chunks
    Done!
    Deleted 19 corrupted chunks

If we have a backup of our world we can use them to fix the problems 
found chunks, this method can spam a lot of output text, because writes 
a log for every chunk that is trying to fix::

    $ python region-fixer.py --backups ~/backup/2013.01.05/ --replace-corrupted ~/.minecraft/saves/corrupted-world
    
    Welcome to Region Fixer!

    ############################################################
    ############ Scanning world: Testing corruption ############
    ############################################################
    Scanning directory...
    Info: No nether dimension in the world directory.
    Info: No end dimension in the world directory.
    There are 1 region files and 1 player files in the world directory.

    -------------------- Checking level.dat --------------------
    'level.dat' is redable

    ------------------ Checking player files -------------------
    All player files are readable.

    ------------------ Scanning the overworld ------------------
    Scanning:  1 /  1 100% [########################################] Time: 00:00:19

    Found 19 corrupted, 0 wrong located chunks and 0 chunks with too many entities of a total of 625

    ############ Trying to replace corrupted chunks ############

    ---------- New chunk to replace! Coords (-16, 9) -----------
    Backup region file found in:
      ~/backup/2013.01.05/region/r.-1.0.mca
    Replacing...
    Chunk replaced using backup dir: ~/backup/2013.01.05/

    ---------- New chunk to replace! Coords (-10, 19) ----------
    Backup region file found in:
      ~/backup/2013.01.05/region/r.-1.0.mca
    Replacing...
    Chunk replaced using backup dir: ~/backup/2013.01.05/

        ... long log of replaced chunks ...

    ---------- New chunk to replace! Coords (-13, 16) ----------
    Backup region file found in:
      ~/backup/2013.01.05/region/r.-1.0.mca
    Replacing...
    Chunk replaced using backup dir: ~/backup/2013.01.05/

    ---------- New chunk to replace! Coords (-13, 25) ----------
    Backup region file found in:
      ~/backup/2013.01.05/region/r.-1.0.mca
    Replacing...
    Chunk replaced using backup dir: ~/backup/2013.01.05/

    19 replaced chunks of a total of 19 corrupted chunks

These options have an equivalent for wrong located chunks.

Another problem that Region Fixer can fix is an entity problem.
Sometimes worlds store thousands of entities in one chunk, hanging the
server when loaded. This can happen with squids, spiders, or even items. 
A very common way to make this happen in your server is to ignite a few 
thousands of TNTs at the same time. All those TNTs are entities and 
the server will hang trying to move them all.

This problem can be fixed with this method. Using the option 
"--delete-entities" Region Fixer will delete all the entities in that 
chunk if it does have more entities than entity-limit (see the help). 
It doesn't touch TileEntities (chests, singposts, noteblocks, etc...). 
At the moment of writing this Entities stored in chunks are:

- mobs
- projectiles (arrows, snowballs...)
- primed TNT
- ender crystal
- paintings
- items on the ground (don't worry chests are safe)
- vehicles (boats and minecarts)
- dynamic tiles (falling sand and activated TNT)

Note that you still need to load the chunk in Region Fixer to fix it, 
and it may need GIGs of RAM and lot of time. You can use this in
combination with "--entity-limit" to set your limit (default 300
entities, note that a chunk has 256 square meters of surface and if you 
put a mob in every sun lighted block of a chunk that will make 256 
mobs, so it's a big limit!)::

    python region-fixer.py --entity-limit 50 --delete-entities ~/.minecraft/saves/corrupted-world

    Welcome to Region Fixer!

    ############################################################
    ############ Scanning world: Testing corruption ############
    ############################################################
    Scanning directory...
    Info: No nether dimension in the world directory.
    Info: No end dimension in the world directory.
    There are 1 region files and 1 player files in the world directory.

    -------------------- Checking level.dat --------------------
    'level.dat' is redable

    ------------------ Checking player files -------------------
    All player files are readable.

    ------------------ Scanning the overworld ------------------
    Deleted 102 entities in chunk (14,8) of the region file: r.-1.0.mca
    Deleted 111 entities in chunk (14,10) of the region file: r.-1.0.mca
    Deleted 84 entities in chunk (15,4) of the region file: r.-1.0.mca
    Deleted 75 entities in chunk (21,4) of the region file: r.-1.0.mca
    Scanning:  1 /  1 100% [########################################] Time: 00:00:20

    Found 0 corrupted, 0 wrong located chunks and 0 chunks with too many entities of a total of 625


From version v0.1.0 there is also an interactive mode for Region-Fixer. 
If you don't know what's wrong with your world this mode can be very
useful. To start using the mode use the '--interactive' option::

    $ python region-fixer.py --interactive ~/.minecraft/saves/corrutped-world

In this mode the scan results are saved in memory, so one scanned you 
can delete chunks, delete entities, replace chunks, replace chunks with
too many entities and read a summary of what's wrong without needing to 
scan the world again. Example of usage::

    $ python region-fixer.py --interactive ~/.minecraft/saves/corrupted-world
    Welcome to Region Fixer!
    Minecraft Region-Fixer interactive mode.
    (Use tab to autocomplete. Type help for a list of commands.)

    #-> scan
    Scanning directory...
    Info: No nether dimension in the world directory.
    Info: No end dimension in the world directory.
    There are 1 region files and 1 player files in the world directory.

    -------------------- Checking level.dat --------------------
    'level.dat' is redable

    ------------------ Checking player files -------------------
    All player files are readable.

    ------------------ Scanning the overworld ------------------
    Scanning:  1 /  1 100% [########################################] Time: 00:00:21
    
    #-> summary
    
    ############################################################
    ############## World name: Testing corruption ##############
    ############################################################

    level.dat:
        'level.dat' is readable

    Player files:
        All player files are readable.

    Overworld:
    Region file: r.-1.0.mca
     |-+-Chunk coords: header (16, 9), global (-16, 9).
     | +-Status: Corrupted
     
        ... big summary...
    
     |-+-Chunk coords: header (19, 25), global (-13, 25).
     | +-Status: Corrupted
     |
     +


    #-> remove_chunks corrupted 
     Deleting chunks in region set "/home/alejandro/.minecraft/saves/corrupted-world/region/": Done! Removed 19 chunks
    Done! Removed 19 chunks
    #-> 


For more info: “python region-fixer.py --help”


Bugs, suggestions, feedback, questions
======================================
Suggestions and bugs should go to the github page:

https://github.com/Fenixin/Minecraft-Region-Fixer

Feedback and questions should go preferably to the forums posts:

(server administration)
http://www.minecraftforum.net/topic/275730-tool-minecraft-region-fixer/

(mapping and modding)
http://www.minecraftforum.net/topic/302380-tool-minecraft-region-fixer/


Contributors
============
See CONTRIBUTORS.txt


Warning
=======
This program has been tested with a lot of worlds, but there may be 
bugs, so please, MAKE A BACKUP OF YOUR WORLD BEFORE RUNNING it,
I'M NOT RESPONSIBLE OF WHAT HAPPENS TO YOUR WORLD. Other way to say it 
is USE THIS TOOL AT YOUR OWN RISK.

Think that you are playing with you precious saved games :P .

Good luck! :)

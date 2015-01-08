======================
Minecraft Region Fixer
======================

By Alejandro Aguilera (Fenixin) 
Sponsored by NITRADO servers (http://nitrado.net)

Locates problems and tries to fix Minecraft worlds (or region files).

Tries to fix corrupted chunks in region files using old backup copies
of the Minecraft world. If you don't have a copy, you can eliminate the
corrupted chunks making Minecraft regenerate them.

It also scans the 'level.dat' file and the player '\*.dat' and tries to 
read them. If there are any problems it prints warnings. At the moment
it doesn't fix any problem in these files.

Web page:
https://github.com/Fenixin/Minecraft-Region-Fixer

Mincraft forums posts:
http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/
http://www.minecraftforum.net/topic/275730-minecraft-region-fixer/

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
regenerate those chunks.

Region-Fixer still is useful for replacing those chunks with a 
backup, removing entities, or trying to see what's going wrong
with your world.


Usage
=====
You can read the program help running: "python region-fixer.py --help"

For usage examples and more info visit the wiki:

https://github.com/Fenixin/Minecraft-Region-Fixer/wiki/Usage


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

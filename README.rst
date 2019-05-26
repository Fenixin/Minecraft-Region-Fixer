======================
Minecraft Region Fixer
======================

By Alejandro Aguilera (Fenixin) 

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
https://www.minecraftforum.net/forums/support/server-support-and/1903200-minecraft-region-fixer
https://www.minecraftforum.net/forums/mapping-and-modding-java-edition/minecraft-tools/1261480-minecraft-region-fixer

Supported platforms
===================
This program only works with Python 3.x, and DOESN'T work with
python 2.x. There was a windows exe in older versions, but right
now you need to install the python interpreter to run this
program.

Notes
=====
Older versions of Minecraft had big problems when loading broken
worlds. Newer versions of Minecraft are doing improving the way
they deal with corruption and other things.

Region-Fixer still is useful for replacing chunks/regions with a 
backup, removing entities, or trying to see what's going wrong
with your world.


Usage
=====
You can read the program help running: "python regionfixer.py --help"

For usage examples and more info visit the wiki:

https://github.com/Fenixin/Minecraft-Region-Fixer/wiki/Usage


Bugs, suggestions, feedback, questions
======================================
Suggestions and bugs should go to the github page:

https://github.com/Fenixin/Minecraft-Region-Fixer

Feedback and questions should go preferably to the forums posts:

(server administration)
https://www.minecraftforum.net/forums/support/server-support-and/1903200-minecraft-region-fixer

(mapping and modding)
https://www.minecraftforum.net/forums/mapping-and-modding-java-edition/minecraft-tools/1261480-minecraft-region-fixer


Donations and sponsors
======================
Region-Fixer was created thanks to sponsors and donations. You can find
information about that in DONORS.txt


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

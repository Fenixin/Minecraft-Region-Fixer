==========================
The NBT library for Python
==========================

Forewords
=========

This is mainly a `Named Binary Tag` parser & writer library.

From the initial specification by Markus Persson::

  NBT (Named Binary Tag) is a tag based binary format designed to carry large
  amounts of binary data with smaller amounts of additional data.
  An NBT file consists of a single GZIPped Named Tag of type TAG_Compound.

Current specification is on the official [Minecraft Wiki](https://minecraft.gamepedia.com/NBT_format).

This library is very suited to inspect & edit the Minecraft data files. Provided
examples demonstrate how to:
- get player and world statistics,
- list mobs, chest contents, biomes,
- draw a simple world map,
- etc.

.. image:: world.png

*Note: Examples are just here to help using and testing the library.
Developing Minecraft tools is out of the scope of this project.*


Status
======

The library supports all the currently known tag types (including the arrays
of 'Integer' and 'Long'), and the examples work with the McRegion,
pre-"flattened" and "flattened" Anvil formats.

Last update was tested on Minecraft version **1.13.2**.


Dependencies
============

The library, the tests and the examples are only using the Python core library,
except `curl` for downloading some test reference data and `PIL` (Python
Imaging Library) for the `map` example.

Supported Python releases: 2.7, 3.4 to 3.7


Usage
=====

Reading files
-------------

The easiest way to read an nbt file is to instantiate an NBTFile object e.g.::

  >>> from nbt import nbt
  >>> nbtfile = nbt.NBTFile("bigtest.nbt",'rb')
  >>> nbtfile.name
  u'Level'
  >>> nbtfile["nested compound test"].tag_info()
  TAG_Compound("nested compound test"): 2 Entries
  >>> for tag in nbtfile["nested compound test"]["ham"].tags:
  ...     print(tag.tag_info())
  ...
  TAG_String("name"): Hampus
  TAG_Float("value"): 0.75
  >>> [tag.value for tag in nbtfile["listTest (long)"].value]
  [11, 12, 13, 14, 15]

Files can also be read from a fileobj (file-like object that contains a compressed
stream) or a buffer (file-like object that contains an uncompressed stream of NBT
Tags) which can be accomplished thusly::

  >>> from nbt.nbt import *
  >>> nbtfile = NBTFile(fileobj=previously_opened_file)
  # or....
  >>> nbtfile = NBTFile(buffer=net_socket.makefile())


Writing files
-------------

Writing files is easy too! if you have a NBTFile object, simply call it's
write_file() method. If the NBTFile was instantiated with a filename, then
write_file needs no extra arguments. It just works. If however you created a new
file object from scratch (or even if you just want to save it somewhere else)
call write_file('path\to\new\file.nbt')::

  >>> from nbt import nbt
  >>> nbtfile = nbt.NBTFile("bigtest.nbt",'rb')
  >>> nbtfile["listTest (compound)"].tags[0]["name"].value = "Different name"
  >>> nbtfile.write_file("newnbtfile.nbt")

It is also possible to write to a buffer or fileobj using the same keyword args::

  >>> nbtfile.write_file(fileobj = my_file) #compressed
  >>> nbtfile.write_file(buffer = sock.makefile()) #uncompressed


Creating files
--------------

Creating files is trickier but ultimately should give you no issue, as long as
you have read the NBT spec (hint.. it's very short). Also be sure to note that
the NBTFile object is actually a TAG_Compound with some wrapper features, so
you can use all the standard tag features::

  >>> from nbt.nbt import *
  >>> nbtfile = NBTFile()


First, don't forget to name the top level tag::

  >>> nbtfile.name = "My Top Level Tag"
  >>> nbtfile.tags.append(TAG_Float(name="My Float Name", value=3.152987593947))
  >>> mylist = TAG_List(name="TestList", type=TAG_Long) #type needs to be pre-declared!
  >>> mylist.tags.append(TAG_Long(100))
  >>> mylist.tags.extend([TAG_Long(120),TAG_Long(320),TAG_Long(19)])
  >>> nbtfile.tags.append(mylist)
  >>> print(nbtfile.pretty_tree())
  TAG_Compound("My Top Level Tag"): 2 Entries
  {
      TAG_Float("My Float Name"): 3.15298759395
      TAG_List("TestList"): 4 entries of type TAG_Long
      {
          TAG_Long: 100
          TAG_Long: 120
          TAG_Long: 320
          TAG_Long: 19
      }
  }
  >>> nbtfile["TestList"].tags.sort(key = lambda tag: tag.value)
  >>> print(nbtfile.pretty_tree())
  TAG_Compound("My Top Level Tag"): 2 Entries
  {
      TAG_Float("My FloatName"): 3.15298759395
      TAG_List("TestList"): 4 entries of type TAG_Long
      {
          TAG_Long: 19
          TAG_Long: 100
          TAG_Long: 120
          TAG_Long: 320
       }
  }
  >>> nbtfile.write_file("mynbt.dat")

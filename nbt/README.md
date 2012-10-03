This is a Named Binary Tag parser based upon the specification by Markus Persson.

From The spec:
  "NBT (Named Binary Tag) is a tag based binary format designed to carry large
   amounts of binary data with smaller amounts of additional data.
   An NBT file consists of a single GZIPped Named Tag of type TAG_Compound."

read the full spec at http://www.minecraft.net/docs/NBT.txt

[![Build Status](https://secure.travis-ci.org/twoolie/NBT.png?branch=master)](http://travis-ci.org/#!/twoolie/NBT)

Usage:
 1) Reading files.

 The easiest way to read an nbt file is to instantiate an NBTFile object e.g.

    >>> import nbt
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
 Tags) which can be accomplished thusly:

    >>> import nbt
    >>> nbtfile = NBTFile(fileobj=previously_opened_file)
    # or....
    >>> nbtfile = NBTFile(buffer=net_socket.makefile())

 2) Writing files.

 Writing files is easy too! if you have a NBTFile object, simply call it's
 write_file() method. If the NBTFile was instantiated with a filename, then
 write_file needs no extra arguments. It just works. If however you created a new
 file object from scratch (or even if you just want to save it somewhere else)
 call write_file('path\to\new\file.nbt')

    >>> import nbt
    >>> nbtfile = nbt.NBTFile("bigtest.nbt",'rb')
    >>> nbtfile["listTest (compound)"].tags[0]["name"].value = "Different name"
    >>> nbtfile.write_file("newnbtfile.nbt")

 It is also possible to write to a buffer or fileobj using the same keyword args.

    >>> nbtfile.write_file(fileobj = my_file) #compressed
    >>> nbtfile.write_file(buffer = sock.makefile()) #uncompressed

 3) Creating files

 Creating files is trickier but ultimately should give you no issue, as long as
 you have read the NBT spec (hint.. it's very short). Also be sure to note that
 the NBTFile object is actually a TAG_Compound with some wrapper features, so
 you can use all the standard tag features

    >>> from nbt import *
    >>> nbtfile = NBTFile()

 first, don't forget to name the top level tag

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

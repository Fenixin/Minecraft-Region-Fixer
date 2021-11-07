"""
Handle the NBT (Named Binary Tag) data format

For more information about the NBT format:
https://minecraft.gamepedia.com/NBT_format
"""

from struct import Struct, error as StructError
from gzip import GzipFile
try:
    from collections.abc import MutableMapping, MutableSequence, Sequence
except ImportError:  # for Python 2.7
    from collections import MutableMapping, MutableSequence, Sequence
import sys

_PY3 = sys.version_info >= (3,)
if _PY3:
    unicode = str
    basestring = str
else:
    range = xrange

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


class MalformedFileError(Exception):
    """Exception raised on parse error."""
    pass


class TAG(object):
    """TAG, a variable with an intrinsic name."""
    id = None

    def __init__(self, value=None, name=None):
        self.name = name
        self.value = value

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        raise NotImplementedError(self.__class__.__name__)

    def _render_buffer(self, buffer):
        raise NotImplementedError(self.__class__.__name__)

    # Printing and Formatting of tree
    def tag_info(self):
        """Return Unicode string with class, name and unnested value."""
        return self.__class__.__name__ + (
            '(%r)' % self.name if self.name
            else "") + ": " + self.valuestr()

    def valuestr(self):
        """Return Unicode string of unnested value. For iterators, this
        returns a summary."""
        return unicode(self.value)

    def namestr(self):
        """Return Unicode string of tag name."""
        return unicode(self.name)

    def pretty_tree(self, indent=0):
        """Return formated Unicode string of self, where iterable items are
        recursively listed in detail."""
        return ("\t" * indent) + self.tag_info()

    # Python 2 compatibility; Python 3 uses __str__ instead.
    def __unicode__(self):
        """Return a unicode string with the result in human readable format.
        Unlike valuestr(), the result is recursive for iterators till at least
        one level deep."""
        return unicode(self.value)

    def __str__(self):
        """Return a string (ascii formated for Python 2, unicode for Python 3)
        with the result in human readable format. Unlike valuestr(), the result
         is recursive for iterators till at least one level deep."""
        return str(self.value)

    # Unlike regular iterators, __repr__() is not recursive.
    # Use pretty_tree for recursive results.
    # iterators should use __repr__ or tag_info for each item, like
    #  regular iterators
    def __repr__(self):
        """Return a string (ascii formated for Python 2, unicode for Python 3)
        describing the class, name and id for debugging purposes."""
        return "<%s(%r) at 0x%x>" % (
            self.__class__.__name__, self.name, id(self))


class _TAG_Numeric(TAG):
    """_TAG_Numeric, comparable to int with an intrinsic name"""

    def __init__(self, value=None, name=None, buffer=None):
        super(_TAG_Numeric, self).__init__(value, name)
        if buffer:
            self._parse_buffer(buffer)

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        # Note: buffer.read() may raise an IOError, for example if buffer is a
        # corrupt gzip.GzipFile
        self.value = self.fmt.unpack(buffer.read(self.fmt.size))[0]

    def _render_buffer(self, buffer):
        buffer.write(self.fmt.pack(self.value))


class _TAG_End(TAG):
    id = TAG_END
    fmt = Struct(">b")

    def _parse_buffer(self, buffer):
        # Note: buffer.read() may raise an IOError, for example if buffer is a
        # corrupt gzip.GzipFile
        value = self.fmt.unpack(buffer.read(1))[0]
        if value != 0:
            raise ValueError(
                "A Tag End must be rendered as '0', not as '%d'." % value)

    def _render_buffer(self, buffer):
        buffer.write(b'\x00')


# == Value Tags ==#
class TAG_Byte(_TAG_Numeric):
    """Represent a single tag storing 1 byte."""
    id = TAG_BYTE
    fmt = Struct(">b")


class TAG_Short(_TAG_Numeric):
    """Represent a single tag storing 1 short."""
    id = TAG_SHORT
    fmt = Struct(">h")


class TAG_Int(_TAG_Numeric):
    """Represent a single tag storing 1 int."""
    id = TAG_INT
    fmt = Struct(">i")
    """Struct(">i"), 32-bits integer, big-endian"""


class TAG_Long(_TAG_Numeric):
    """Represent a single tag storing 1 long."""
    id = TAG_LONG
    fmt = Struct(">q")


class TAG_Float(_TAG_Numeric):
    """Represent a single tag storing 1 IEEE-754 floating point number."""
    id = TAG_FLOAT
    fmt = Struct(">f")


class TAG_Double(_TAG_Numeric):
    """Represent a single tag storing 1 IEEE-754 double precision floating
    point number."""
    id = TAG_DOUBLE
    fmt = Struct(">d")


class TAG_Byte_Array(TAG, MutableSequence):
    """
    TAG_Byte_Array, comparable to a collections.UserList with
    an intrinsic name whose values must be bytes
    """
    id = TAG_BYTE_ARRAY

    def __init__(self, name=None, buffer=None):
        # TODO: add a value parameter as well
        super(TAG_Byte_Array, self).__init__(name=name)
        if buffer:
            self._parse_buffer(buffer)

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Int(buffer=buffer)
        self.value = bytearray(buffer.read(length.value))

    def _render_buffer(self, buffer):
        length = TAG_Int(len(self.value))
        length._render_buffer(buffer)
        buffer.write(bytes(self.value))

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        # TODO: check type of value
        self.value[key] = value

    def __delitem__(self, key):
        del (self.value[key])

    def insert(self, key, value):
        # TODO: check type of value, or is this done by self.value already?
        self.value.insert(key, value)

    # Printing and Formatting of tree
    def valuestr(self):
        return "[%i byte(s)]" % len(self.value)

    def __unicode__(self):
        return '[' + ",".join([unicode(x) for x in self.value]) + ']'

    def __str__(self):
        return '[' + ",".join([str(x) for x in self.value]) + ']'


class TAG_Int_Array(TAG, MutableSequence):
    """
    TAG_Int_Array, comparable to a collections.UserList with
    an intrinsic name whose values must be integers
    """
    id = TAG_INT_ARRAY

    def __init__(self, name=None, buffer=None):
        # TODO: add a value parameter as well
        super(TAG_Int_Array, self).__init__(name=name)
        if buffer:
            self._parse_buffer(buffer)

    def update_fmt(self, length):
        """ Adjust struct format description to length given """
        self.fmt = Struct(">" + str(length) + "i")

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Int(buffer=buffer).value
        self.update_fmt(length)
        self.value = list(self.fmt.unpack(buffer.read(self.fmt.size)))

    def _render_buffer(self, buffer):
        length = len(self.value)
        self.update_fmt(length)
        TAG_Int(length)._render_buffer(buffer)
        buffer.write(self.fmt.pack(*self.value))

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    def __delitem__(self, key):
        del (self.value[key])

    def insert(self, key, value):
        self.value.insert(key, value)

    # Printing and Formatting of tree
    def valuestr(self):
        return "[%i int(s)]" % len(self.value)


class TAG_Long_Array(TAG, MutableSequence):
    """
    TAG_Long_Array, comparable to a collections.UserList with
    an intrinsic name whose values must be integers
    """
    id = TAG_LONG_ARRAY

    def __init__(self, name=None, buffer=None):
        super(TAG_Long_Array, self).__init__(name=name)
        if buffer:
            self._parse_buffer(buffer)

    def update_fmt(self, length):
        """ Adjust struct format description to length given """
        self.fmt = Struct(">" + str(length) + "q")

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Int(buffer=buffer).value
        self.update_fmt(length)
        self.value = list(self.fmt.unpack(buffer.read(self.fmt.size)))

    def _render_buffer(self, buffer):
        length = len(self.value)
        self.update_fmt(length)
        TAG_Int(length)._render_buffer(buffer)
        buffer.write(self.fmt.pack(*self.value))

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    def __delitem__(self, key):
        del (self.value[key])

    def insert(self, key, value):
        self.value.insert(key, value)

    # Printing and Formatting of tree
    def valuestr(self):
        return "[%i long(s)]" % len(self.value)


class TAG_String(TAG, Sequence):
    """
    TAG_String, comparable to a collections.UserString with an
    intrinsic name
    """
    id = TAG_STRING

    def __init__(self, value=None, name=None, buffer=None):
        super(TAG_String, self).__init__(value, name)
        if buffer:
            self._parse_buffer(buffer)

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Short(buffer=buffer)
        read = buffer.read(length.value)
        if len(read) != length.value:
            raise StructError()
        self.value = read.decode("utf-8")

    def _render_buffer(self, buffer):
        save_val = self.value.encode("utf-8")
        length = TAG_Short(len(save_val))
        length._render_buffer(buffer)
        buffer.write(save_val)

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    # Printing and Formatting of tree
    def __repr__(self):
        return self.value


# == Collection Tags ==#
class TAG_List(TAG, MutableSequence):
    """
    TAG_List, comparable to a collections.UserList with an intrinsic name
    """
    id = TAG_LIST

    def __init__(self, type=None, value=None, name=None, buffer=None):
        super(TAG_List, self).__init__(value, name)
        if type:
            self.tagID = type.id
        else:
            self.tagID = None
        self.tags = []
        if buffer:
            self._parse_buffer(buffer)
        # if self.tagID == None:
        #     raise ValueError("No type specified for list: %s" % (name))

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        self.tagID = TAG_Byte(buffer=buffer).value
        self.tags = []
        length = TAG_Int(buffer=buffer)
        for x in range(length.value):
            self.tags.append(TAGLIST[self.tagID](buffer=buffer))

    def _render_buffer(self, buffer):
        TAG_Byte(self.tagID)._render_buffer(buffer)
        length = TAG_Int(len(self.tags))
        length._render_buffer(buffer)
        for i, tag in enumerate(self.tags):
            if tag.id != self.tagID:
                raise ValueError(
                    "List element %d(%s) has type %d != container type %d" %
                    (i, tag, tag.id, self.tagID))
            tag._render_buffer(buffer)

    # Mixin methods
    def __len__(self):
        return len(self.tags)

    def __iter__(self):
        return iter(self.tags)

    def __contains__(self, item):
        return item in self.tags

    def __getitem__(self, key):
        return self.tags[key]

    def __setitem__(self, key, value):
        self.tags[key] = value

    def __delitem__(self, key):
        del (self.tags[key])

    def insert(self, key, value):
        self.tags.insert(key, value)

    # Printing and Formatting of tree
    def __repr__(self):
        return "%i entries of type %s" % (
            len(self.tags), TAGLIST[self.tagID].__name__)

    # Printing and Formatting of tree
    def valuestr(self):
        return "[%i %s(s)]" % (len(self.tags), TAGLIST[self.tagID].__name__)

    def __unicode__(self):
        return "[" + ", ".join([tag.tag_info() for tag in self.tags]) + "]"

    def __str__(self):
        return "[" + ", ".join([tag.tag_info() for tag in self.tags]) + "]"

    def pretty_tree(self, indent=0):
        output = [super(TAG_List, self).pretty_tree(indent)]
        if len(self.tags):
            output.append(("\t" * indent) + "{")
            output.extend([tag.pretty_tree(indent + 1) for tag in self.tags])
            output.append(("\t" * indent) + "}")
        return '\n'.join(output)


class TAG_Compound(TAG, MutableMapping):
    """
    TAG_Compound, comparable to a collections.OrderedDict with an
    intrinsic name
    """
    id = TAG_COMPOUND

    def __init__(self, buffer=None, name=None):
        # TODO: add a value parameter as well
        super(TAG_Compound, self).__init__()
        self.tags = []
        if name:
            self.name = name
        else:
            self.name = ""
        if buffer:
            self._parse_buffer(buffer)

    # Parsers and Generators
    def _parse_buffer(self, buffer):
        while True:
            type = TAG_Byte(buffer=buffer)
            if type.value == TAG_END:
                # print("found tag_end")
                break
            else:
                name = TAG_String(buffer=buffer).value
                try:
                    tag = TAGLIST[type.value]()
                except KeyError:
                    raise ValueError("Unrecognised tag type %d" % type.value)
                tag.name = name
                self.tags.append(tag)
                tag._parse_buffer(buffer)

    def _render_buffer(self, buffer):
        for tag in self.tags:
            TAG_Byte(tag.id)._render_buffer(buffer)
            TAG_String(tag.name)._render_buffer(buffer)
            tag._render_buffer(buffer)
        buffer.write(b'\x00')  # write TAG_END

    # Mixin methods
    def __len__(self):
        return len(self.tags)

    def __iter__(self):
        for key in self.tags:
            yield key.name

    def __contains__(self, key):
        if isinstance(key, int):
            return key <= len(self.tags)
        elif isinstance(key, basestring):
            for tag in self.tags:
                if tag.name == key:
                    return True
            return False
        elif isinstance(key, TAG):
            return key in self.tags
        return False

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.tags[key]
        elif isinstance(key, basestring):
            for tag in self.tags:
                if tag.name == key:
                    return tag
            else:
                raise KeyError("Tag %s does not exist" % key)
        else:
            raise TypeError(
                "key needs to be either name of tag, or index of tag, "
                "not a %s" % type(key).__name__)

    def __setitem__(self, key, value):
        assert isinstance(value, TAG), "value must be an nbt.TAG"
        if isinstance(key, int):
            # Just try it. The proper error will be raised if it doesn't work.
            self.tags[key] = value
        elif isinstance(key, basestring):
            value.name = key
            for i, tag in enumerate(self.tags):
                if tag.name == key:
                    self.tags[i] = value
                    return
            self.tags.append(value)

    def __delitem__(self, key):
        if isinstance(key, int):
            del (self.tags[key])
        elif isinstance(key, basestring):
            self.tags.remove(self.__getitem__(key))
        else:
            raise ValueError(
                "key needs to be either name of tag, or index of tag")

    def keys(self):
        return [tag.name for tag in self.tags]

    def iteritems(self):
        for tag in self.tags:
            yield (tag.name, tag)

    # Printing and Formatting of tree
    def __unicode__(self):
        return "{" + ", ".join([tag.tag_info() for tag in self.tags]) + "}"

    def __str__(self):
        return "{" + ", ".join([tag.tag_info() for tag in self.tags]) + "}"

    def valuestr(self):
        return '{%i Entries}' % len(self.tags)

    def pretty_tree(self, indent=0):
        output = [super(TAG_Compound, self).pretty_tree(indent)]
        if len(self.tags):
            output.append(("\t" * indent) + "{")
            output.extend([tag.pretty_tree(indent + 1) for tag in self.tags])
            output.append(("\t" * indent) + "}")
        return '\n'.join(output)


TAGLIST = {TAG_END: _TAG_End, TAG_BYTE: TAG_Byte, TAG_SHORT: TAG_Short,
           TAG_INT: TAG_Int, TAG_LONG: TAG_Long, TAG_FLOAT: TAG_Float,
           TAG_DOUBLE: TAG_Double, TAG_BYTE_ARRAY: TAG_Byte_Array,
           TAG_STRING: TAG_String, TAG_LIST: TAG_List,
           TAG_COMPOUND: TAG_Compound, TAG_INT_ARRAY: TAG_Int_Array,
           TAG_LONG_ARRAY: TAG_Long_Array}


class NBTFile(TAG_Compound):
    """Represent an NBT file object."""

    def __init__(self, filename=None, buffer=None, fileobj=None):
        """
        Create a new NBTFile object.
        Specify either a filename, file object or data buffer.
        If filename of file object is specified, data should be GZip-compressed.
        If a data buffer is specified, it is assumed to be uncompressed.

        If filename is specified, the file is closed after reading and writing.
        If file object is specified, the caller is responsible for closing the
        file.
        """
        super(NBTFile, self).__init__()
        self.filename = filename
        self.type = TAG_Byte(self.id)
        closefile = True
        # make a file object
        if filename:
            self.filename = filename
            self.file = GzipFile(filename, 'rb')
        elif buffer:
            if hasattr(buffer, 'name'):
                self.filename = buffer.name
            self.file = buffer
            closefile = False
        elif fileobj:
            if hasattr(fileobj, 'name'):
                self.filename = fileobj.name
            self.file = GzipFile(fileobj=fileobj)
        else:
            self.file = None
            closefile = False
        # parse the file given initially
        if self.file:
            self.parse_file()
            if closefile:
                # Note: GzipFile().close() does NOT close the fileobj,
                # So we are still responsible for closing that.
                try:
                    self.file.close()
                except (AttributeError, IOError):
                    pass
            self.file = None

    def parse_file(self, filename=None, buffer=None, fileobj=None):
        """Completely parse a file, extracting all tags."""
        closefile = True
        if filename:
            self.file = GzipFile(filename, 'rb')
        elif buffer:
            if hasattr(buffer, 'name'):
                self.filename = buffer.name
            self.file = buffer
            closefile = False
        elif fileobj:
            if hasattr(fileobj, 'name'):
                self.filename = fileobj.name
            self.file = GzipFile(fileobj=fileobj)
        if self.file:
            try:
                type = TAG_Byte(buffer=self.file)
                if type.value == self.id:
                    name = TAG_String(buffer=self.file).value
                    self._parse_buffer(self.file)
                    self.name = name
                    if closefile:
                        self.file.close()
                else:
                    raise MalformedFileError(
                        "First record is not a Compound Tag")
            except StructError as e:
                raise MalformedFileError(
                    "Partial File Parse: file possibly truncated.")
        else:
            raise ValueError(
                "NBTFile.parse_file(): Need to specify either a "
                "filename or a file object"
            )

    def write_file(self, filename=None, buffer=None, fileobj=None):
        """Write this NBT file to a file."""
        closefile = True
        if buffer:
            self.filename = None
            self.file = buffer
            closefile = False
        elif filename:
            self.filename = filename
            self.file = GzipFile(filename, "wb")
        elif fileobj:
            self.filename = None
            self.file = GzipFile(fileobj=fileobj, mode="wb")
        elif self.filename:
            self.file = GzipFile(self.filename, "wb")
        elif not self.file:
            raise ValueError(
                "NBTFile.write_file(): Need to specify either a "
                "filename or a file object"
            )
        # Render tree to file
        TAG_Byte(self.id)._render_buffer(self.file)
        TAG_String(self.name)._render_buffer(self.file)
        self._render_buffer(self.file)
        # make sure the file is complete
        try:
            self.file.flush()
        except (AttributeError, IOError):
            pass
        if closefile:
            try:
                self.file.close()
            except (AttributeError, IOError):
                pass

    def __repr__(self):
        """
        Return a string (ascii formated for Python 2, unicode
        for Python 3) describing the class, name and id for
        debugging purposes.
        """
        if self.filename:
            return "<%s(%r) with %s(%r) at 0x%x>" % (
                self.__class__.__name__, self.filename,
                TAG_Compound.__name__, self.name, id(self)
            )
        else:
            return "<%s with %s(%r) at 0x%x>" % (
                self.__class__.__name__, TAG_Compound.__name__,
                self.name, id(self)
            )

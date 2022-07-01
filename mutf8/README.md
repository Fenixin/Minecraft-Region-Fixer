![Tests](https://github.com/TkTech/mutf8/workflows/Tests/badge.svg?branch=master)

# mutf-8

This package contains simple pure-python as well as C encoders and decoders for
the MUTF-8 character encoding. In most cases, you can also parse the even-rarer
CESU-8.

These days, you'll most likely encounter MUTF-8 when working on files or
protocols related to the JVM. Strings in a Java `.class` file are encoded using
MUTF-8, strings passed by the JNI, as well as strings exported by the object
serializer.

This library was extracted from [Lawu][], a Python library for working with JVM
class files.

## 🎉 Installation

Install the package from PyPi:

```
pip install mutf8
```

Binary wheels are available for the following:

|                  | py3.6 | py3.7 | py3.8 | py3.9 |
| ---------------- | ----- | ----- | ----- | ----- |
| OS X (x86_64)    | y     | y     | y     | y     |
| Windows (x86_64) | y     | y     | y     | y     |
| Linux (x86_64)   | y     | y     | y     | y     |

If binary wheels are not available, it will attempt to build the C extension
from source with any C99 compiler. If it could not build, it will fall back
to a pure-python version.

## Usage

Encoding and decoding is simple:

```python
from mutf8 import encode_modified_utf8, decode_modified_utf8

unicode = decode_modified_utf8(byte_like_object)
bytes = encode_modified_utf8(unicode)
```

This module *does not* register itself globally as a codec, since importing
should be side-effect-free.

## 📈 Benchmarks

The C extension is significantly faster - often 20x to 40x faster.

<!-- BENCHMARK START -->

### MUTF-8 Decoding
| Name                         |   Min (μs) |   Max (μs) |   StdDev |           Ops |
|------------------------------|------------|------------|----------|---------------|
| cmutf8-decode_modified_utf8  |    0.00009 |    0.00080 |  0.00000 | 9957678.56358 |
| pymutf8-decode_modified_utf8 |    0.00190 |    0.06040 |  0.00000 |  450455.96019 |

### MUTF-8 Encoding
| Name                         |   Min (μs) |   Max (μs) |   StdDev |            Ops |
|------------------------------|------------|------------|----------|----------------|
| cmutf8-encode_modified_utf8  |    0.00008 |    0.00151 |  0.00000 | 11897361.05101 |
| pymutf8-encode_modified_utf8 |    0.00180 |    0.16650 |  0.00000 |   474390.98091 |
<!-- BENCHMARK END -->

## C Extension

The C extension is optional. If a binary package is not available, or a C
compiler is not present, the pure-python version will be used instead. If you
want to ensure you're using the C version, import it directly:

```python
from mutf8.cmutf8 import decode_modified_utf8

decode_modified_utf(b'\xED\xA1\x80\xED\xB0\x80')
```

[Lawu]: https://github.com/tktech/lawu

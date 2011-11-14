from distutils.core import setup
import nbt
import py2exe

setup(console=['region-fixer.py'], data_files=['scan.py','world.py','progressbar.py','COPYING.txt','README.rst','CONTRIBUTORS.txt'])

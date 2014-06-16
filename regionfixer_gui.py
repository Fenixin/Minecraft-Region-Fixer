#!/usr/bin/env python
# -*- coding: utf-8 -*-

from multiprocessing import freeze_support
import sys

# Needed for the gui
import regionfixer_core
import nbt

from gui import Starter
if __name__ == '__main__':
    freeze_support()
    s = Starter()
    value = s.run()
    sys.exit(value)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import platform

# stolen from minecraft overviewer 
# https://github.com/overviewer/Minecraft-Overviewer/
def is_bare_console():
    """Returns true if Overviewer is running in a bare console in
    Windows, that is, if overviewer wasn't started in a cmd.exe
    session.
    """
    if platform.system() == 'Windows':
        try:
            import ctypes
            GetConsoleProcessList = ctypes.windll.kernel32.GetConsoleProcessList
            num = GetConsoleProcessList(ctypes.byref(ctypes.c_int(0)), ctypes.c_int(1))
            if (num == 1):
                return True
                
        except Exception:
            pass
    return False

def entitle(text, level = 0):
    # print simple titles
    t = ''
    if level == 0:
        t += "\n"
        t += "{0:#^60}\n".format('')
        t += "{0:#^60}\n".format(' ' + text + ' ')
        t += "{0:#^60}\n".format('')
    return t
        

def table(columns):
    """ Gets a list with lists in which each list is a column,
        returns a text string with a table. """

    def get_max_len(l):
        """ Takes a list and returns the length of the biggest
            element """
        m = 0
        for e in l:
            if len(str(e)) > m:
                m = len(e)
        return m

    text = ""
    # stores the size of the biggest element in that column
    ml = []
    # fill up ml
    for c in columns:
        m = 0
        t = get_max_len(c)
        if t > m:
            m = t
        ml.append(m)
    # get the total width of the table:
    ml_total = 0
    for i in range(len(ml)):
        ml_total += ml[i] + 2 # size of each word + 2 spaces
    ml_total += 1 + 2# +1 for the separator | and +2 for the borders
    text += "-"*ml_total + "\n"
    # all the columns have the same number of rows
    row = get_max_len(columns)
    for r in range(row):
        line = "|"
        # put all the elements in this row together with spaces
        for i in range(len(columns)):
            line += "{0: ^{width}}".format(columns[i][r],width = ml[i] + 2)
            # add a separator for the first column
            if i == 0:
                line += "|"

        text += line + "|" + "\n"
        if r == 0:
            text += "-"*ml_total + "\n"
    text += "-"*ml_total
    return text

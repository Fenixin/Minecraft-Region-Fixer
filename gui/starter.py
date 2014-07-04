#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

from main import MainWindow
from backups import BackupsWindow
from about import AboutWindow
from help import HelpWindow


class Starter(object):
    def __init__(self):
        """ Create the windows and set some variables. """

        self.app = wx.App(False)

        self.frame = MainWindow(None, "Region-Fixer-GUI")
        # NOTE: It's very important that the MainWindow is parent of all others windows
        self.backups = BackupsWindow(self.frame, "Backups")
        self.about = AboutWindow(self.frame, "About")
        self.frame.backups = self.backups
        self.frame.about = self.about
        self.frame.help = HelpWindow(self.frame, "Help")

    def run(self):
        """ Run the app main loop. """

        self.app.MainLoop()

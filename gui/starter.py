#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import sys
import traceback
from io import StringIO

from .main import MainWindow
from .backups import BackupsWindow
from .about import AboutWindow
from .help import HelpWindow

from regionfixer_core.scan import ChildProcessException
from regionfixer_core.bug_reporter import BugReporter
from regionfixer_core.util import get_str_from_traceback

ERROR_MSG = "\n\nOps! Something went really wrong and regionfixer crashed.\n\nI can try to send an automatic bug rerpot if you wish.\n"
QUESTION_TEXT = ('Do you want to send an anonymous bug report to the region fixer ftp?\n'
                 '(Answering no will print the bug report)')

# Thanks to:
# http://wxpython-users.1045709.n5.nabble.com/Exception-handling-strategies-td2369185.html
# For a way to handle exceptions
class MyApp(wx.App):
    def OnInit(self):
        sys.excepthook = self._excepthook
        return True

    def _excepthook(self, etype, value, tb):
        if isinstance(etype, ChildProcessException):
            s = "Using GUI:\n\n" + value.printable_traceback
        else:
            s = "Using GUI:\n\n" + get_str_from_traceback(etype, value, tb)
            # bug - display a dialog with the entire exception and traceback printed out
        traceback.print_tb(tb)
        dlg = wx.MessageDialog(self.main_window,
                               ERROR_MSG + "\n" + QUESTION_TEXT,
                               style=wx.ICON_ERROR | wx.YES_NO)
        # Get a string with the traceback and send it
        
        answer = dlg.ShowModal()
        if answer == wx.ID_YES:
            print("Sending bug report!")
            bugsender = BugReporter(error_str=s)
            success = bugsender.send()
            # Dialog with success or not of the ftp uploading
            if success:
                msg = "The bug report was successfully uploaded."
                style = 0
            else:
                msg = "Couldn't upload the bug report!\n\nPlease, try again later."
                style = wx.ICON_ERROR
            dlg = wx.MessageDialog(self.main_window, msg, style=style)
            dlg.ShowModal()
        else:
            dlg = wx.MessageDialog(self.main_window, "Error msg:\n\n" + s,
                               style=wx.ICON_ERROR)
            dlg.ShowModal()


class Starter(object):
    def __init__(self):
        """ Create the windows and set some variables. """

        self.app = MyApp(False)

        self.frame = MainWindow(None, "Region-Fixer-GUI")
        # NOTE: It's very important that the MainWindow is parent of all others windows
        self.backups = BackupsWindow(self.frame, "Backups")
        self.about = AboutWindow(self.frame, "About")
        self.frame.backups = self.backups
        self.frame.about = self.about
        self.frame.help = HelpWindow(self.frame, "Help")
#         self.frame.error = ErrorWindow(self.frame, "Error")

        self.app.main_window = self.frame

    def run(self):
        """ Run the app main loop. """

        self.app.MainLoop()

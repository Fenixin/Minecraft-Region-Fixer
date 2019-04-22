#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
from time import sleep
from os.path import split, abspath
from os import name as os_name

from .backups import BackupsWindow
from regionfixer_core.scan import AsyncWorldRegionScanner, AsyncDataScanner,\
    ChildProcessException
from regionfixer_core import world
from regionfixer_core.world import World

if os_name == 'nt':
    # Proper way to set an icon in windows 7 and above
    # Thanks to http://stackoverflow.com/a/15923439
    import ctypes
    myappid = 'Fenixin.region-fixer.gui.100'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


class MainWindow(wx.Frame):
    def __init__(self, parent, title, backups=None):
        wx.Frame.__init__(self, parent, title=title, size=(300, 400))
        # Every windows should use panel as parent. Not doing so will
        # make the windows look non-native (very ugly)
        panel = wx.Panel(self)

        self.backups = backups

        # Icon
        ico = wx.Icon('icon.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(ico)

        # Open world stuff
        self.last_path = ""  # Last path opened
        self.world = None  # World to scan

        # Status bar
        self.CreateStatusBar()

        # Create menu
        filemenu = wx.Menu()
        windowsmenu = wx.Menu()
        helpmenu = wx.Menu()

        # Add elements to filemenu
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open", "Open a Minecraft world")
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit","Terminate program")

        # Add elements to helpmenu
        menuHelp = helpmenu.Append(wx.ID_HELP, "&Help", "Where to find help")
        helpmenu.AppendSeparator()
        menuAbout = helpmenu.Append(wx.ID_ABOUT, "&About", "Information about this program")

        # Add elements to windowsmenu
        menuBackups = windowsmenu.Append(-1, "&Backups", "Manage list of backups")
#         menuAdvanced = windowsmenu.Append(-1, "A&dvanced actions", "Manage list of backups")

        # Create a menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File")
        menuBar.Append(windowsmenu,"&View")
        menuBar.Append(helpmenu,"&Help")
        self.SetMenuBar(menuBar)

        # Create elements in the window
        # First row:
        self.status_text = wx.StaticText(panel, style=wx.TE_MULTILINE, label="No world loaded")
        self.open_button = wx.Button(panel, label="Open")
        self.scan_button = wx.Button(panel, label="Scan")
        self.scan_button.Disable()
        self.firstrow_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.firstrow_sizer.Add(self.status_text, 1,  wx.ALIGN_CENTER)
        self.firstrow_sizer.Add(self.open_button, 0, wx.EXPAND)
        self.firstrow_sizer.Add(self.scan_button, 0, wx.EXPAND)
        self.firstrow_static_box = wx.StaticBox(panel, label="World loaded")
        self.firstrow_static_box_sizer = wx.StaticBoxSizer(self.firstrow_static_box)
        self.firstrow_static_box_sizer.Add(self.firstrow_sizer, 1, wx.EXPAND)

        # Second row:
        self.proc_info_text = wx.StaticText(panel, label="Processes to use: ")
        self.proc_text = wx.TextCtrl(panel, value="1", size=(30, 24), style=wx.TE_CENTER)
        self.el_info_text = wx.StaticText(panel, label="Entity limit: " )
        self.el_text = wx.TextCtrl(panel, value="150", size=(50, 24), style=wx.TE_CENTER)
        self.secondrow_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.secondrow_sizer.Add(self.proc_info_text, flag=wx.ALIGN_CENTER)
        self.secondrow_sizer.Add(self.proc_text, 0, flag=wx.RIGHT | wx.ALIGN_LEFT, border=15)
        self.secondrow_sizer.Add(self.el_info_text, 0, wx.ALIGN_CENTER)
        self.secondrow_sizer.Add(self.el_text, 0, wx.ALIGN_RIGHT)
        self.secondrow_static_box_sizer = wx.StaticBoxSizer(wx.StaticBox(panel, label="Scan options"))
        self.secondrow_static_box_sizer.Add(self.secondrow_sizer, 1, flag=wx.EXPAND)

        # Third row:
        # Note: In order to use a static box add it directly to a 
        # static box sizer and add to the same sizer it's contents
        self.results_text = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_MULTILINE, value="Scan the world to get results", size = (500,200))
        # Lets try to create a monospaced font:
        ffont = wx.Font(9, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
#         print ffont.IsFixedWidth()
        textattr = wx.TextAttr(font = ffont)
        self.results_text.SetFont(ffont)
        self.results_text_box = wx.StaticBox(panel, label="Results", size = (100,100))
        self.results_text_box_sizer = wx.StaticBoxSizer(self.results_text_box)
        self.results_text_box_sizer.Add(self.results_text, 1, wx.EXPAND)

        self.delete_all_chunks_button = wx.Button(panel, label = "Delete all bad chunks")
        self.replace_all_chunks_button = wx.Button(panel, label = "Replace all bad chunks (using backups)")
        self.delete_all_regions_button = wx.Button(panel, label = "Delete all bad regions")
        self.replace_all_regions_button = wx.Button(panel, label = "Replace all bad regions (using backups)")
        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

        self.thirdrow_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.thirdrow_actions_box = wx.StaticBox(panel, label="Actions", size = (-1,-1))
        self.thirdrow_buttons_box_sizer = wx.StaticBoxSizer(self.thirdrow_actions_box)
        self.thirdrow_buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        self.thirdrow_buttons_sizer.Add(self.delete_all_chunks_button, 1, wx.EXPAND)
        self.thirdrow_buttons_sizer.Add(self.replace_all_chunks_button, 1, wx.EXPAND)
        self.thirdrow_buttons_sizer.Add(self.delete_all_regions_button, 1, wx.EXPAND)
        self.thirdrow_buttons_sizer.Add(self.replace_all_regions_button, 1, wx.EXPAND)
        self.thirdrow_buttons_box_sizer.Add(self.thirdrow_buttons_sizer, 1, wx.EXPAND)
        self.thirdrow_sizer.Add(self.results_text_box_sizer, 1, wx.EXPAND)
        self.thirdrow_sizer.Add(self.thirdrow_buttons_box_sizer, 0, wx.EXPAND)

        # All together now
        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)
        self.frame_sizer.Add(self.firstrow_static_box_sizer, 0, wx.EXPAND)
        self.frame_sizer.Add(self.secondrow_static_box_sizer, 0, wx.EXPAND)
        self.frame_sizer.Add(self.thirdrow_sizer, 1, wx.EXPAND)

        # Layout sizers
        panel.SetSizerAndFit(self.frame_sizer)

        self.frame_sizer.Fit(self)

        # Bindings
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnHelp, menuHelp)
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnBackups, menuBackups)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_BUTTON, self.OnScan, self.scan_button)
        self.Bind(wx.EVT_BUTTON, self.OnOpen, self.open_button)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteChunks, self.delete_all_chunks_button)
        self.Bind(wx.EVT_BUTTON, self.OnReplaceChunks, self.replace_all_chunks_button)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteRegions, self.delete_all_regions_button)
        self.Bind(wx.EVT_BUTTON, self.OnReplaceRegions, self.replace_all_regions_button)

        self.Show(True)

    def OnExit(self, e):
        self.Close(True)

    def OnBackups(self, e):
        self.backups.Show(True)

    def OnAbout(self, e):
        self.about.Show(True)
    
    def OnHelp(self, e):
        self.help.Show(True)

    def OnOpen(self, e):
        """ Called when the open world button is pressed. """
        dlg = wx.DirDialog(self, "Choose a Minecraft world folder")
        # Set the last path used
        dlg.SetPath(self.last_path)
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = dlg.GetPath()
            # Check if it's a minecraft world
            w = World(self.dirname)
            if not w.isworld:
                error = wx.MessageDialog(self, "This directory doesn't look like a Minecraft world", "Error", wx.ICON_EXCLAMATION)
                error.ShowModal()
                error.Destroy()
            else:
                # Insert it in the ListBox
                self.world = w
                self.update_world_status(self.world)

        # Properly recover the last path used
        self.last_path = split(dlg.GetPath())[0]
        dlg.Destroy()

        # Rest the results textctrl
        self.results_text.SetValue("")


    def OnScan(self, e):
        """ Called when the scan button is pressed. """
        processes = int(self.proc_text.GetValue())
        entity_limit = int(self.el_text.GetValue())
        delete_entities = False

        ps = AsyncDataScanner(self.world.players, processes)
        ops = AsyncDataScanner(self.world.old_players, processes)
        ds = AsyncDataScanner(self.world.data_files, processes)
        ws = AsyncWorldRegionScanner(self.world, processes, entity_limit,
                       delete_entities)

        things_to_scan = [ws, ops, ps, ds]
        dialog_texts = ["Scanning region files",
                        "Scanning old format player files",
                        "Scanning players",
                        "Scanning data files"]
        try:
            for scanner, dialog_title in zip(things_to_scan, dialog_texts):
                progressdlg = wx.ProgressDialog(
                            dialog_title,
                            "Last scanned:\n starting...",
                            len(scanner), self,
                            style=wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME |
                                  wx.PD_REMAINING_TIME | wx.PD_CAN_ABORT |
                                  wx.PD_AUTO_HIDE | wx.PD_SMOOTH)
                scanner.scan()
                counter = 0
                # NOTE TO SELF: ShowModal behaves different in windows and Linux!
                # Use it with care.
                progressdlg.Show()
                while not scanner.finished:
                    sleep(0.001)
                    result = scanner.get_last_result()

                    if result:
                        counter += 1
                    not_cancelled, not_skipped = progressdlg.Update(counter,
                                       "Last scanned:\n" + scanner.str_last_scanned)
                    if not not_cancelled:
                        # User pressed cancel
                        scanner.terminate()
                        break
                progressdlg.Destroy()
                if not not_cancelled:
                    break
            else:
                # The scan finished successfully
                self.world.scanned = True
                self.results_text.SetValue(self.world.generate_report(True))
                self.update_delete_buttons_status(True)
                self.update_replace_buttons_status(True)
        except ChildProcessException as e:
            # Will be handled in starter.py by _excepthook()
            scanner.terminate()
            progressdlg.Destroy()
            raise e
            #===================================================================
            # error_log_path = e.save_error_log()
            # filename = e.scanned_file.filename
            # scanner.terminate()
            # progressdlg.Destroy()
            # error = wx.MessageDialog(self,
            #              ("Something went really wrong scanning {0}\n\n"
            #               "This is probably an error in the code. Please, "
            #               "if you have the time report it. "
            #               "I have saved all the error information in:\n\n"
            #               "{1}").format(filename, error_log_path),
            #                                 "Error",
            #                                 wx.ICON_ERROR)
            # error.ShowModal()
            #===================================================================

    def OnDeleteChunks(self, e):
        progressdlg = wx.ProgressDialog("Removing chunks", "This may take a while", 
            self.world.count_regions(), self,
            style=wx.PD_ELAPSED_TIME |
                wx.PD_ESTIMATED_TIME |
                wx.PD_REMAINING_TIME |
                wx.PD_CAN_SKIP |
                wx.PD_CAN_ABORT |
                wx.PD_AUTO_HIDE |
                wx.PD_SMOOTH
            )
        progressdlg = progressdlg
        progressdlg.Pulse()
        remove_chunks = self.world.remove_problematic_chunks
        for problem in world.CHUNK_PROBLEMS:
            progressdlg.Pulse("Removing chunks with problem: {}".format(world.CHUNK_STATUS_TEXT[problem]))
            remove_chunks(problem)
        progressdlg.Destroy()
        progressdlg.Destroy()

        self.results_text.SetValue("Scan again the world for results.")
        self.update_delete_buttons_status(False)
        self.update_delete_buttons_status(False)

    def OnDeleteRegions(self, e):
        progressdlg = wx.ProgressDialog("Removing regions", "This may take a while...", 
            self.world.count_regions(), self,
            style=wx.PD_ELAPSED_TIME |
            wx.PD_ESTIMATED_TIME |
            wx.PD_REMAINING_TIME |
            wx.PD_AUTO_HIDE |
            wx.PD_SMOOTH
            )
        progressdlg = progressdlg
        progressdlg.Pulse()
        remove_regions = self.world.remove_problematic_regions
        for problem in world.REGION_PROBLEMS:
            progressdlg.Pulse("Removing regions with problem: {}".format(world.REGION_STATUS_TEXT[problem]))
            remove_regions(problem)
        progressdlg.Destroy()

        self.results_text.SetValue("Scan again the world for results.")
        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

    def OnReplaceChunks(self, e):
        # Get options
        entity_limit = int(self.el_text.GetValue())
        delete_entities = False

        progressdlg = wx.ProgressDialog("Removing chunks", "Removing...",
            self.world.count_regions(), self,
            style=wx.PD_ELAPSED_TIME |
            wx.PD_ESTIMATED_TIME |
            wx.PD_REMAINING_TIME |
            wx.PD_AUTO_HIDE |
            wx.PD_SMOOTH
            )
        progressdlg = progressdlg
        backups = self.backups.world_list
        progressdlg.Pulse()
        replace_chunks = self.world.replace_problematic_chunks
        for problem in world.CHUNK_PROBLEMS:
            progressdlg.Pulse("Replacing chunks with problem: {}".format(world.CHUNK_STATUS_TEXT[problem]))
            replace_chunks(backups, problem, entity_limit, delete_entities)
        progressdlg.Destroy()

        self.results_text.SetValue("Scan again the world for results.")
        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

    def OnReplaceRegions(self, e):
        # Get options
        entity_limit = int(self.el_text.GetValue())
        delete_entities = False
        progressdlg = wx.ProgressDialog("Removing regions", "Removing...", 
            self.world.count_regions(), self, 
            style = wx.PD_ELAPSED_TIME | 
            wx.PD_ESTIMATED_TIME | 
            wx.PD_REMAINING_TIME | 
            #~ wx.PD_CAN_SKIP | 
            #~ wx.PD_CAN_ABORT | 
            wx.PD_AUTO_HIDE |
            wx.PD_SMOOTH
            )
        progressdlg = progressdlg
        backups = self.backups.world_list
        progressdlg.Pulse()
        replace_regions = self.world.replace_problematic_regions
        for problem in world.REGION_PROBLEMS:
            progressdlg.Pulse("Replacing regions with problem: {}".format(world.REGION_STATUS_TEXT[problem]))
            replace_regions(backups, problem, entity_limit, delete_entities)
        progressdlg.Destroy()

        self.results_text.SetValue("Scan again the world for results.")
        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

    def update_delete_buttons_status(self, status):

        if status:
            self.delete_all_chunks_button.Enable()
            self.delete_all_regions_button.Enable()
        else:
            self.delete_all_chunks_button.Disable()
            self.delete_all_regions_button.Disable()

    def update_replace_buttons_status(self, status):

        if status:
            self.replace_all_chunks_button.Enable()
            self.replace_all_regions_button.Enable()
        else:
            self.replace_all_chunks_button.Disable()
            self.replace_all_regions_button.Disable()

    def update_world_status(self, world):
        self.status_text.SetLabel(world.path)
        self.scan_button.Enable()

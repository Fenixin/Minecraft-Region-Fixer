#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import os
from time import sleep
from os.path import split

from backups import BackupsWindow
from regionfixer_core.scan import AsyncWorldScanner, AsyncPlayerScanner
from regionfixer_core import world
from regionfixer_core.world import World


class MainWindow(wx.Frame):
    def __init__(self, parent, title, backups = None):
        wx.Frame.__init__(self, parent, title=title, size = (300,400))
        
        panel = wx.Panel(self)
        
        self.backups = backups
        
        # Variables
        self.last_path = "" # Last path opened
        self.world = None # World to scan
        
        # Status bar
        self.CreateStatusBar()
        
        # Create menu
        filemenu=wx.Menu()
        windowsmenu = wx.Menu()
        helpmenu = wx.Menu()

        # Add elements to filemenu
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open", "Open a Minecraft world")
        filemenu.AppendSeparator()
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit","Terminate program")
        
        # Add elements to helpmenu
        menuAbout = helpmenu.Append(wx.ID_ABOUT, "&About", "Information about this program")
        
        # Add elements to windowsmenu
        menuBackups = windowsmenu.Append(-1, "&Backups", "Manage list of backups")
        menuAdvanced = windowsmenu.Append(-1, "A&dvanced actions", "Manage list of backups")
        
        # Create a menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File")
        menuBar.Append(windowsmenu,"&View")
        menuBar.Append(helpmenu,"&Help")
        self.SetMenuBar(menuBar)
        
        # Create elements in the window
        # First row:
        
        self.status_text = wx.StaticText(panel, style=wx.TE_MULTILINE, label="test")
        self.open_button = wx.Button(panel, label="Open")
        self.scan_button = wx.Button(panel, label="Scan")
        self.scan_button.Disable()
        self.firstrow_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.firstrow_sizer.Add(self.status_text, 1,  wx.ALIGN_CENTER)
        self.firstrow_sizer.Add(self.open_button, 0, wx.EXPAND)
        self.firstrow_sizer.Add(self.scan_button, 0, wx.EXPAND)
        self.firstrow_static_box = wx.StaticBox(panel, label = "World loaded")
        self.firstrow_static_box_sizer = wx.StaticBoxSizer(self.firstrow_static_box)
        self.firstrow_static_box_sizer.Add(self.firstrow_sizer, 1, wx.EXPAND)
        
        
        # Second row:
        self.proc_info_text = wx.StaticText(panel, label="Threads to use: ")
        self.proc_text = wx.TextCtrl(panel, value="1")
        self.el_info_text = wx.StaticText(panel, label="Entity limit: " )
        self.el_text = wx.TextCtrl(panel, value="150")
        self.secondrow_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.secondrow_sizer.Add(self.proc_info_text, 0, wx.ALIGN_CENTER)
        self.secondrow_sizer.Add(self.proc_text, 0, wx.ALIGN_LEFT)
        self.secondrow_sizer.Add(self.el_info_text, 0, wx.ALIGN_CENTER)
        self.secondrow_sizer.Add(self.el_text, 0, wx.ALIGN_RIGHT)
        self.secondrow_static_box_sizer = wx.StaticBoxSizer(wx.StaticBox(panel, label = "Scan options"))
        self.secondrow_static_box_sizer.Add(self.secondrow_sizer, 1, wx.EXPAND)
        
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
        
    def OnOpen(self, e):
        dlg = wx.DirDialog(self, "Choose a Minecraf world folder")
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
        self.last_path = os.path.split(dlg.GetPath())[0]
        dlg.Destroy()
        
        # Rest the results textctrl
        self.results_text.SetValue("")

    def OnDeleteChunks(self, e):
        progressdlg = wx.ProgressDialog("Removing chunks", "Removing...", 
            self.world.count_regions(), self, 
            style = wx.PD_ELAPSED_TIME | 
            wx.PD_ESTIMATED_TIME | 
            wx.PD_REMAINING_TIME | 
            wx.PD_CAN_SKIP | 
            wx.PD_CAN_ABORT | 
            wx.PD_AUTO_HIDE |
            wx.PD_SMOOTH
            )
        progressdlg = progressdlg
        progressdlg.Pulse()
        self.world.remove_problematic_chunks(world.CHUNK_CORRUPTED)
        progressdlg.Pulse()
        print "1"
        self.world.remove_problematic_chunks(world.CHUNK_SHARED_OFFSET)
        progressdlg.Pulse()
        print "2"
        self.world.remove_problematic_chunks(world.CHUNK_WRONG_LOCATED)
        progressdlg.Pulse()
        print "3"
        self.world.remove_problematic_chunks(world.CHUNK_TOO_MANY_ENTITIES)
        progressdlg.Pulse()
        print "4"
        progressdlg.Destroy()
        
        self.update_delete_buttons_status(False)

    def OnDeleteRegions(self, e):
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
        
        self.world.remove_problematic_regions(world.REGION_TOO_SMALL)
        progressdlg.pulse()
        self.world.remove_problematic_regions(world.REGION_UNREADABLE)
        progressdlg.pulse()
        progressdlg.Destroy()
        
        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

    def OnReplaceChunks(self, e):
        progressdlg = wx.ProgressDialog("Removing chunks", "Removing...", 
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
        
        self.world.replace_problematic_chunks(world.CHUNK_CORRUPTED, backups)
        progressdlg.pulse()
        self.world.replace_problematic_chunks(world.CHUNK_SHARED_OFFSET, backups)
        progressdlg.pulse()
        self.world.replace_problematic_chunks(world.CHUNK_WRONG_LOCATED, backups)
        progressdlg.pulse()
        self.world.replace_problematic_chunks(world.CHUNK_TOO_MANY_ENTITIES, backups)
        progressdlg.pulse()
        progressdlg.Destroy()
        
        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

    def OnReplaceRegions(self, e):
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
        
        self.world.remove_problematic_regions(world.REGION_TOO_SMALL)
        progressdlg.pulse()
        self.world.remove_problematic_regions(world.REGION_UNREADABLE)
        progressdlg.pulse()
        progressdlg.Destroy()

        self.update_delete_buttons_status(False)
        self.update_replace_buttons_status(False)

    def OnScan(self, e):
        # Let's simulate the options stuff
        class Options(object):
            def __init__(self, main):
                self.entity_limit = int(main.el_text.GetValue())
                self.processes = int(main.proc_text.GetValue())
                self.verbose = True
                self.delete_entities = False
                self.gui = True

        options = Options(self)
        progressdlg = wx.ProgressDialog("Scanning...", "Scanning...",
            self.world.count_regions(), self,
            style=wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME |
                  wx.PD_REMAINING_TIME | wx.PD_CAN_SKIP | wx.PD_CAN_ABORT |
                  wx.PD_AUTO_HIDE | wx.PD_SMOOTH)
        options.progressdlg = progressdlg

        ws = AsyncWorldScanner(self.world, options.processes,
                               options.entity_limit,
                               options.delete_entities)
        ws.scan()
        counter = 0
        while not ws.finished:
            sleep(0.001)
            result = ws.get_last_result()
            rs = ws.current_regionset
            if result:
                counter += 1
            progressdlg.Update(counter,
                               "Scanning regions from: " + rs.get_name())

        progressdlg.Destroy()

        # TODO: DATA files and old player files
        progressdlg = wx.ProgressDialog("Scanning...", "Scanning...",
            self.world.count_regions(), self,
            style=wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME |
                  wx.PD_REMAINING_TIME | wx.PD_CAN_SKIP | wx.PD_CAN_ABORT |
                  wx.PD_AUTO_HIDE | wx.PD_SMOOTH)

        ps = AsyncPlayerScanner(self.world.players, options.processes)
        ps.scan()
        counter = 0
        last_player = ""
        while not ps.finished:
            sleep(0.0001)
            result = ps.get_last_result()
            if result:
                counter += 1
                last_player = result.filename.split('.')[0]
            progressdlg.Update(counter,
                               "Last player scanned: " + last_player)

        progressdlg.Destroy()

        # Data files
        progressdlg = wx.ProgressDialog("Scanning...", "Scanning...",
            self.world.count_regions(), self,
            style=wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME |
                  wx.PD_REMAINING_TIME | wx.PD_CAN_SKIP | wx.PD_CAN_ABORT |
                  wx.PD_AUTO_HIDE | wx.PD_SMOOTH)

        ps = AsyncPlayerScanner(self.world.players, options.processes)
        ps.scan()
        counter = 0
        last_player = ""
        while not ps.finished:
            sleep(0.001)
            result = ps.get_last_result()
            if result:
                counter += 1
                last_player = result.filename.split('.')[0]
            progressdlg.Update(counter,
                               "Last player scanned: " + last_player)

        progressdlg.Destroy()


        self.results_text.SetValue(self.world.generate_report(True))
        self.update_delete_buttons_status(True)
        

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

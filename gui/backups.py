#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import os

# TODO: just copied this file to this module, is a cutre solution
# improve it! See Importing python modules from relative paths, or
# order this in a better way
from regionfixer_core.world import World


class BackupsWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title)
        # Every windows should use panel as parent. Not doing so will
        # make the windows look non-native (very ugly)
        panel = wx.Panel(self)

        # Sizer with all the elements in the window
        self.all_sizer = wx.BoxSizer(wx.VERTICAL)

        # Text with help in the top
        self.help_text = wx.StaticText(panel, style=wx.TE_MULTILINE,
                                       label=("Region-Fixer will use the worlds in\n"
                                              "this list in top-down order."))

        # List of worlds to use as backups
        self.world_list_box = wx.ListBox(panel, size=(180, 100))
        test_list = []
        self.world_list_box.Set(test_list)
        # Here will be the worlds to use as backup
        self.world_list = test_list[:]
        self.world_list_text = test_list[:]
        # Last path we used in the file dialog
        self.last_path = ""

        # Buttons
        self.buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.add = wx.Button(panel, label="Add")
        self.move_up = wx.Button(panel, label="Move up")
        self.move_down = wx.Button(panel, label="Move down")
        self.buttons_sizer.Add(self.add, 0, 0)
        self.buttons_sizer.Add(self.move_up, 0, 0)
        self.buttons_sizer.Add(self.move_down, 0, 0)

        # Add things to the general sizer
        self.all_sizer.Add(self.help_text, proportion=0,
                           flag=wx.GROW | wx.ALL, border=10)
        self.all_sizer.Add(self.world_list_box, proportion=1,
                           flag=wx.EXPAND | wx.ALL, border=10)
        self.all_sizer.Add(self.buttons_sizer, proportion=0,
                           flag=wx.ALIGN_CENTER | wx.ALL, border=10)

        # Layout sizers
        panel.SetSizerAndFit(self.all_sizer)

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_BUTTON, self.OnAddWorld, self.add)
        self.Bind(wx.EVT_BUTTON, self.OnMoveUp, self.move_up)
        self.Bind(wx.EVT_BUTTON, self.OnMoveDown, self.move_down)

        # Show the window, usually False, True for fast testing
        self.Show(False)

    def get_dirs(self, list_dirs):
        """ From a list of paths return only the directories. """

        tmp = []
        for p in self.dirnames:
            if os.path.isdir(p):
                tmp.append(p)
        return tmp

    def are_there_files(self, list_dirs):
        """ Given a list of paths return True if there are any files. """

        for d in list_dirs:
            if not os.path.isdir(d):
                return True
        return False

    def OnAddWorld(self, e):
        """ Called when the buttom Add is clicked. """

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
                self.world_list.append(w)
                index = self.world_list.index(w)
                # TODO check if it's a minecraft world
                self.world_list_box.InsertItems([w.name], pos = index)
        
        # Properly recover the last path used
        self.last_path = os.path.split(dlg.GetPath())[0]
        dlg.Destroy()

    def get_selected_index(self, list_box):
        """ Returns the index of the selected item in a list_box. """

        index = None
        for i in range(len(self.world_list)):
            if list_box.IsSelected(i):
                index = i
        return index

    def move_left_inlist(self, l, index):
        """ Move the element in the list with index to the left. 
        
        Return the index where the moved element is. 
        
        """

        tmp = l.pop(index)
        index = index - 1 if index != 0 else 0
        l.insert(index, tmp)

        return index
        
    def move_right_inlist(self, l, index):
        """ Move the element in the list with index to the right. 

        Return the index where the moved element is. 

        """

        len_l = len(l)
        tmp = l.pop(index)
        index = index + 1
        if index == len_l:
            l.append(tmp)
            index = len_l - 1
        else:
            l.insert(index, tmp)

        return index
    
    def get_names_from_worlds(self, world_list):
        """ Return a list of names from a list of worlds in order. """

        t = []
        for i in world_list:
            t.append(i.name)
        return t

    def OnMoveUp(self, e):
        """ Move up in the world list the selected item. """

        index = self.get_selected_index(self.world_list_box)

        if index is not None:
            index = self.move_left_inlist(self.world_list, index)
            #~ self.world_list_box.Set(self.world_list)
            self.world_list_box.Set(self.get_names_from_worlds(self.world_list))
            self.world_list_box.Select(index)

    def OnMoveDown(self, e):
        """ Move down in the world list the selected item. """

        index = self.get_selected_index(self.world_list_box)
        len_world_list = len(self.world_list)

        if index is not None:
            index = self.move_right_inlist(self.world_list, index)
            self.world_list_box.Set(self.get_names_from_worlds(self.world_list))
            #~ self.world_list_box.Set(self.world_list)
            self.world_list_box.Select(index)

    def OnClose(self, e):
        """ Ran when the user closes this window. """
        self.Show(False)

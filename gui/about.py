#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx


class AboutWindow(wx.Frame):
    def __init__(self, parent, title = "About"):
        wx.Frame.__init__(self, parent, title=title, style = wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.CAPTION)
        
        self.about1 = wx.StaticText(self, style=wx.ALIGN_CENTER, label="Minecraft Region-Fixer (GUI)")
        self.about2 = wx.StaticText(self, style=wx.ALIGN_CENTER, label="Fix problems in Minecraft worlds.")
        self.about3 = wx.StaticText(self, style=wx.ALIGN_CENTER, label="Official-web:")
        self.link_github = \
            wx.HyperlinkCtrl(self, wx.ID_ABOUT, 
            "https://github.com/Fenixin/Minecraft-Region-Fixer", 
            "https://github.com/Fenixin/Minecraft-Region-Fixer", 
            style = wx.ALIGN_CENTER)
        self.about4 = wx.StaticText(self, style=wx.TE_MULTILINE | wx.ALIGN_CENTER, label="Minecraft forums post:")
        self.link_minecraft_forums = \
            wx.HyperlinkCtrl(self, wx.ID_ABOUT, 
            "http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/", 
            "http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/", 
            style = wx.ALIGN_CENTER)
        
        self.close_button = wx.Button(self, wx.ID_CLOSE)
            
            
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.about1, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        self.sizer.Add(self.about2, 0, wx.ALIGN_CENTER)
        self.sizer.Add(self.about3, 0, wx.ALIGN_CENTER| wx.TOP, 20)
        self.sizer.Add(self.link_github, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.about4, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        self.sizer.Add(self.link_minecraft_forums, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.close_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizerAndFit(self.sizer)
        size = self.sizer.GetMinSize()
        self.SetMinSize(size)
        self.SetMaxSize(size)
        
        
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.close_button)
        
    def OnClose(self, e):
        self.Show(False)
        






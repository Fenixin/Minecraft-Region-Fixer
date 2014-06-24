#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

from regionfixer_core.version import version_string as rf_ver
from gui.version import version_string as gui_ver


class AboutWindow(wx.Frame):
    def __init__(self, parent, title="About"):
        wx.Frame.__init__(self, parent, title=title,
                          style=wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.CAPTION)
        # Every windows should use panel as parent. Not doing so will
        # make the windows look non-native (very ugly)
        panel = wx.Panel(self)

        self.about1 = wx.StaticText(panel, style=wx.ALIGN_CENTER,
                                    label="Minecraft Region-Fixer (GUI) (ver. {0})\n(using Region-Fixer ver. {1})".format(gui_ver,rf_ver))
        self.about2 = wx.StaticText(panel, style=wx.ALIGN_CENTER,
                                    label="Fix problems in Minecraft worlds.")
        self.about3 = wx.StaticText(panel, style=wx.ALIGN_CENTER,
                                    label="Official-web:")
        self.link_github = wx.HyperlinkCtrl(panel, wx.ID_ABOUT,
                        "https://github.com/Fenixin/Minecraft-Region-Fixer",
                        "https://github.com/Fenixin/Minecraft-Region-Fixer",
                        style=wx.ALIGN_CENTER)
        self.about4 = wx.StaticText(panel,
                                    style=wx.TE_MULTILINE | wx.ALIGN_CENTER,
                                    label="Minecraft forums post:")
        self.link_minecraft_forums = wx.HyperlinkCtrl(panel, wx.ID_ABOUT,
            "http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/",
            "http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/",
            style=wx.ALIGN_CENTER)

        self.close_button = wx.Button(panel, wx.ID_CLOSE)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.about1, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        self.sizer.Add(self.about2, 0, wx.ALIGN_CENTER| wx.TOP, 20)
        self.sizer.Add(self.about3, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        self.sizer.Add(self.link_github, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.about4, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        self.sizer.Add(self.link_minecraft_forums, 0,wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.close_button, 0, wx.ALIGN_CENTER | wx.ALL, 20)

        # Fit sizers and make the windows not resizable
        panel.SetSizerAndFit(self.sizer)
        self.sizer.Fit(self)
        size = self.GetSize()
        self.SetMinSize(size)
        self.SetMaxSize(size)

        self.Bind(wx.EVT_BUTTON, self.OnClose, self.close_button)

    def OnClose(self, e):
        self.Show(False)

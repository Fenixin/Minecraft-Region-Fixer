#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx

class HelpWindow(wx.Frame):
    def __init__(self, parent, title="Help"):
        wx.Frame.__init__(self, parent, title=title,
                          style=wx.CLOSE_BOX | wx.RESIZE_BORDER | wx.CAPTION)
        # Every windows should use panel as parent. Not doing so will
        # make the windows look non-native (very ugly)
        panel = wx.Panel(self)

        self.help1 = wx.StaticText(panel, style=wx.ALIGN_CENTER,
                label="If you need help you can give a look to the wiki:")
        self.link_github = wx.HyperlinkCtrl(panel, wx.ID_ABOUT,
                        "https://github.com/Fenixin/Minecraft-Region-Fixer/wiki",
                        style=wx.ALIGN_CENTER,
                        url="https://github.com/Fenixin/Minecraft-Region-Fixer/wiki")
        self.help2 = wx.StaticText(panel,
                                    style=wx.TE_MULTILINE | wx.ALIGN_CENTER,
                                    label="Or ask in the minecraft forums:")
        self.link_minecraft_forums = wx.HyperlinkCtrl(panel, wx.ID_ABOUT,
            "http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/",
            "http://www.minecraftforum.net/topic/302380-minecraft-region-fixer/",
            style=wx.ALIGN_CENTER)

        self.close_button = wx.Button(panel, wx.ID_CLOSE)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.help1, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        self.sizer.Add(self.link_github, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(self.help2, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        self.sizer.Add(self.link_minecraft_forums, 0, wx.ALIGN_CENTER | wx.ALL, 5)
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

#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman

**Product Home Page:** http://www.makehuman.org/

**Code Home Page:**    http://code.google.com/p/makehuman/

**Authors:**           Manuel Bastioni, Marc Flerackers, Jonas Hauquier

**Copyright(c):**      MakeHuman Team 2001-2013

**Licensing:**         AGPL3 (see also http://www.makehuman.org/node/318)

**Coding Standards:**  See http://www.makehuman.org/node/165

Abstract
--------

TODO
"""

import os
import mh
import gui3d
import gui
import log

class ThemeRadioButton(gui.RadioButton):

    def __init__(self, group, label, theme):
        self.theme = theme
        checked = (gui3d.app.settings.get('guiTheme', 'default') == self.theme)
        super(ThemeRadioButton, self).__init__(group, label, checked)
        
    def onClicked(self, event):
        gui3d.app.settings['guiTheme'] = self.theme
        gui3d.app.setTheme(self.theme)

class PlatformRadioButton(gui.RadioButton):

    def __init__(self, group, looknfeel):
        super(PlatformRadioButton, self).__init__(group, looknfeel, gui3d.app.getLookAndFeel().lower() == looknfeel.lower())
        self.looknfeel = looknfeel
        
    def onClicked(self, event):
        gui3d.app.setLookAndFeel(self.looknfeel)
        
class LanguageRadioButton(gui.RadioButton):

    def __init__(self, group, language):
        super(LanguageRadioButton, self).__init__(group, language.capitalize(), gui3d.app.settings.get('language', 'english') == language)
        self.language = language
        
    def onClicked(self, event):
    
        gui3d.app.settings['language'] = self.language
        gui3d.app.setLanguage(self.language)
        gui3d.app.prompt('Info', 'You need to restart for your language changes to be applied.', 'OK', helpId='languageHelp')  

class SettingsTaskView(gui3d.TaskView):

    def __init__(self, category):
        gui3d.TaskView.__init__(self, category, 'General')

        sliderBox = self.addLeftWidget(gui.GroupBox('Slider behavior'))
        self.realtimeUpdates = sliderBox.addWidget(gui.CheckBox("Update real-time",
            gui3d.app.settings.get('realtimeUpdates', True)))
        self.realtimeNormalUpdates = sliderBox.addWidget(gui.CheckBox("Update normals real-time",
            gui3d.app.settings.get('realtimeNormalUpdates', True)))
        self.realtimeFitting = sliderBox.addWidget(gui.CheckBox("Fit objects real-time",
            gui3d.app.settings.get('realtimeFitting', False)))
        self.cameraAutoZoom = sliderBox.addWidget(gui.CheckBox("Auto-zoom camera",
            gui3d.app.settings.get('cameraAutoZoom', True)))
        self.sliderImages = sliderBox.addWidget(gui.CheckBox("Slider images",
            gui3d.app.settings.get('sliderImages', True)))
            
        modes = [] 
        unitBox = self.unitsBox = self.addLeftWidget(gui.GroupBox('Units'))
        metric = unitBox.addWidget(gui.RadioButton(modes, 'Metric', gui3d.app.settings.get('units', 'metric') == 'metric'))
        imperial = unitBox.addWidget(gui.RadioButton(modes, 'Imperial', gui3d.app.settings.get('units', 'metric') == 'imperial'))

        preloadBox = self.addLeftWidget(gui.GroupBox('Preloading'))
        self.preload = preloadBox.addWidget(gui.CheckBox("Preload macro targets",
            gui3d.app.settings.get('preloadTargets', False)))
        
        themes = []
        themesBox = self.themesBox = self.addRightWidget(gui.GroupBox('Theme'))
        self.themeNative = themesBox.addWidget(ThemeRadioButton(themes, "Native look", "default"))
        self.themeMH = themesBox.addWidget(ThemeRadioButton(themes, "MakeHuman", "makehuman"))

        initSizeBox = self.addLeftWidget(gui.GroupBox('Initial window size'))
        self.initSizeText = initSizeBox.addWidget(gui.TextEdit(
            str(gui3d.app.settings.get('InitWinWidth', gui3d.app.mainwin.width())) + "x" +
            str(gui3d.app.settings.get('InitWinHeight', gui3d.app.mainwin.height()))))
        
        # For debugging themes on multiple platforms
        '''
        platforms = []
        platformsBox = self.platformsBox = self.addRightWidget(gui.GroupBox('Look and feel'))
        for platform in gui3d.app.getLookAndFeelStyles():
            platformsBox.addWidget(PlatformRadioButton(platforms, platform))
        '''

        languages = []
        languageBox = self.languageBox = self.addRightWidget(gui.GroupBox('Language'))
        languageBox.addWidget(LanguageRadioButton(languages, 'english'))
        
        languageFiles = [os.path.basename(filename).replace('.ini', '') for filename in os.listdir(mh.getSysDataPath('languages')) if filename.split(os.extsep)[-1] == "ini"]
        for language in languageFiles:
            languageBox.addWidget(LanguageRadioButton(languages, language))
        
        @self.realtimeUpdates.mhEvent
        def onClicked(event):
            gui3d.app.settings['realtimeUpdates'] = self.realtimeUpdates.selected
            
        @self.realtimeNormalUpdates.mhEvent
        def onClicked(event):
            gui3d.app.settings['realtimeNormalUpdates'] = self.realtimeNormalUpdates.selected

        @self.realtimeFitting.mhEvent
        def onClicked(event):
            gui3d.app.settings['realtimeFitting'] = self.realtimeFitting.selected
 
        @self.cameraAutoZoom.mhEvent
        def onClicked(event):
            gui3d.app.settings['cameraAutoZoom'] = self.cameraAutoZoom.selected

        @self.sliderImages.mhEvent
        def onClicked(event):
            gui3d.app.settings['sliderImages'] = self.sliderImages.selected
            gui.Slider.showImages(self.sliderImages.selected)
            mh.refreshLayout()

        @self.initSizeText.mhEvent
        def onChange(value):
            try:
                value = value.replace(" ", "")
                res = [int(x) for x in value.split("x")]
                gui3d.app.settings['InitWinWidth'] = res[0]
                gui3d.app.settings['InitWinHeight'] = res[1]
            except: # The user hasn't typed the value correctly yet.
                pass
            
        @metric.mhEvent
        def onClicked(event):
            gui3d.app.settings['units'] = 'metric'
            
        @imperial.mhEvent
        def onClicked(event):
            gui3d.app.settings['units'] = 'imperial'

        @self.preload.mhEvent
        def onClicked(event):
            gui3d.app.settings['preloadTargets'] = self.preload.selected

    def onShow(self, event):
        gui3d.TaskView.onShow(self, event)
    
    def onHide(self, event):
        gui3d.TaskView.onHide(self, event)
        gui3d.app.saveSettings()

def load(app):
    category = app.getCategory('Settings')
    taskview = category.addTask(SettingsTaskView(category))

    app.mainwin.resize(
        app.settings.get('InitWinWidth', app.mainwin.width()),
        app.settings.get('InitWinHeight', app.mainwin.height()))

def unload(app):
    pass



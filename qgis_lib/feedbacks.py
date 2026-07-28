# -*- coding: utf-8 -*-
"""
/***************************************************************************
 qgis-lib-mc
 PyQGIS utilities library to develop plugins or scripts
                             -------------------
        begin                : 2019-02-21
        author               : Mathieu Chailloux
        email                : mathieu.chailloux@irstea.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

"""
    Feedback classes to use as QgsProcessingFeedback.
"""

import time
import datetime

from qgis.core import (
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsMessageLog,
    Qgis)
from qgis.PyQt.QtCore import  QCoreApplication

from . import utils
from . import qgsUtils

from qgis.PyQt.QtGui import QGuiApplication
from qgis.PyQt.QtWidgets import QMessageBox

progressFeedback = None

### Log GUI-free

pluginName = "LightPollutionToolbox"

def debug(msg):
    QgsMessageLog.logMessage(msg,tag=pluginName,level=Qgis.Info)
def info(msg):
    QgsMessageLog.logMessage(msg,tag=pluginName,level=Qgis.Info)
def warn(msg):
    QgsMessageLog.logMessage(msg,tag=pluginName,level=Qgis.Warning)

###

def beginSection(msg):
    if progressFeedback:
        progressFeedback.beginSection(msg)
    else:
        utils.debug("No progress feedback")
        
def endSection():
    if progressFeedback:
        progressFeedback.endSection()
        progressFeedback.setProgress(100)
        
def setProgressText(text):
    if progressFeedback:
        progressFeedback.setProgressText(text)
        
def setSubText(text):
    if progressFeedback:
        progressFeedback.setSubText(text)
        
def endJob():
    if progressFeedback:
        progressFeedback.endJob()
  
def tr(msg):
    return QCoreApplication.translate(None, msg)
def launchDialog(origin,title,msg):
    QMessageBox.information(origin,title,msg)
def paramError(msg,parent=None):
    title = tr("Wrong parameter value")
    launchDialog(parent,title,msg)
def launchQuestionDialog(origin,title,msg):
    reply = QMessageBox.question(origin,title,msg,QMessageBox.Yes,QMessageBox.No)
    return reply
    

class ProgressFeedback(QgsProcessingFeedback):
    
    GDAL_ERROR_PREFIX = 'ERROR '
    SET_COLOR_ERROR = 'ERROR 6:'
    SET_COLOR_MSG = 'SetColorTable'
    FILE_NOT_FOUND_ERROR = 'FileNotFoundError'
    
    def __init__(self,dlg):
        self.dlg = dlg
        self.progressBar = dlg.progressBar
        self.fileFeedback = None
        self.sectionText = ""
        self.sectionHeader = "********"
        self.debug_flag = False
        if not self.dlg.txtLog:
            raise utils.CustomException("No 'txtLog' widget in dialog")
        if not self.dlg.lblProgress:
            raise utils.CustomException("No 'lblProgress' widget in dialog")
        super().__init__()
        
    def setWorkspace(self,workspace):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        outFile = utils.joinPath(workspace,"log.txt")
        utils.removeFile(outFile)
        self.fileFeedback = outFile
        self.pushInfo("Log file " + str(outFile) + " created")
        
    def print_func(self,msg):
        self.dlg.txtLog.append(msg)
        if self.fileFeedback:
            with open(self.fileFeedback,"a+") as f:
                f.write(msg + "\n")

    def printDate(self,msg):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.print_func ("[" + date_str + "] " + msg)
        
    def pushDebugInfo(self,msg):
        if self.debug_flag:
            self.printDate("<font color=\"gray\">[debug] " + msg + "</font>")
        
    def pushInfo(self,msg):
        self.printDate("<font color=\"black\">[info] " + msg + "</font>")
        
    def pushWarning(self,msg):
        self.printDate("<font color=\"orange\">[warn] " + msg + "</font>")
    
    def mkBoldRed(self,msg):
        return "<b><font color=\"red\">" + msg + "</font></b>"
        
    def error_msg(self,msg,prefix=""):
        self.printDate(self.mkBoldRed("[" + prefix + "] " + msg))
        
    def user_error(self,msg,fatal=True):
        self.error_msg(msg,"user error")
        if fatal:
            raise utils.CustomException(msg)
        
    def internal_error(self,msg,fatal=True):
        self.error_msg(msg,"internal error")
        if fatal:
            raise utils.CustomException(msg)
        
    def todo_error(self,msg,fatal=True):
        self.error_msg(msg,"Feature not yet implemented")
        if fatal:
            raise utils.CustomException(msg)
        
    def reportError(self,error,fatalError=False):
        error_msg = str(error)
        if self.SET_COLOR_ERROR in error_msg and self.SET_COLOR_MSG in error_msg:
            self.pushWarning(error_msg)
        elif fatalError:
            self.internal_error("reportError : " + error_msg)
        elif error_msg.startswith(self.FILE_NOT_FOUND_ERROR):
            self.user_error(error_msg)
        else:
            self.internal_error(error_msg)
            #self.pushWarning(error_msg)
        
    def setProgressText(self,txt):
        self.dlg.lblProgress.setText(txt)
        
    def beginSection(self,txt):
        self.sectionText = txt
        self.setProgressText(txt)
        self.setProgress(0)
        self.start_time = time.time()
        self.pushInfo(self.sectionHeader + " BEGIN : " + txt)
        
    def endSection(self):
        if self.sectionText:
            self.setSubText("DONE")
        self.end_time = time.time()
        diff_time = self.end_time - self.start_time
        self.pushInfo(self.sectionHeader + " END : " + self.sectionText + " in " + str(diff_time) + " seconds")
        msg = "{} ... DONE".format(self.sectionText)
        launchDialog(self.dlg,self.tr("Process finished"),msg)
        self.setProgress(100)
        self.sectionText = ""
            
    def setSubText(self,txt):
        self.setProgressText(txt)
        
    def setProgressText(self,text):
        msg = self.sectionText
        if msg:
            msg += "...  "
        msg += text
        self.dlg.lblProgress.setText(msg)
        QGuiApplication.processEvents()
        
    def setProgress(self,value):
        fv = float(value)
        # self.pushDebugInfo("fv = " + str(fv))
        if str(fv) == 'inf':
            self.pushInfo("Unexpected value in progress bar : " + str(value))
        else:
            self.progressBar.setValue(int(value))
        
    def setPercentage(self,percentage):
        pass
        #utils.info("setperc")
        #utils.internal_error("percentage : " + str(percentage))
        
    def focusLogTab(self):
        # self.dlg.mTabWidget.setCurrentWidget(self.dlg.logTab)
        max = self.dlg.txtLog.verticalScrollBar().maximum()
        self.pushDebugInfo("focusLogTab " + str(max))
        self.dlg.txtLog.verticalScrollBar().setValue(max)
        
    def endJob(self):
        # self.setProgress(100)
        self.focusLogTab()
        
    def initGui(self):
        self.dlg.debugButton.setChecked(self.debug_flag)
        
    def connectComponents(self):
        self.dlg.debugButton.clicked.connect(self.switchDebugMode)
        self.dlg.logSaveAs.clicked.connect(self.saveLogAs)
        self.dlg.logClear.clicked.connect(self.myClearLog)
        self.progressChanged.connect(self.setProgress)
        
    def switchDebugMode(self):
        if self.dlg.debugButton.isChecked():
            self.debug_flag = True
            self.pushInfo("Debug mode activated")
        else:
            self.debug_flag = False
            self.pushInfo("Debug mode deactivated")
            
    def saveLogAs(self):
        txt = self.dlg.txtLog.toPlainText()
        fname = qgsUtils.saveFileDialog(self.dlg,msg="Enregistrer le journal sous",filter="*.txt")
        if fname!="":
            utils.writeFile(fname,txt)
            self.pushInfo("Log saved to file '" + fname + "'")
        
    def myClearLog(self):
        self.dlg.txtLog.clear()
        

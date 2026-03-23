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
    Specific class to connect a log view with debug mode.
    See BioDispersal and FragScape for use cases.
"""

from . import utils, qgsUtils

class LogConnector:
    
    def __init__(self,dlg):
        self.dlg = dlg
    
    def initGui(self):
        self.dlg.debugButton.setChecked(utils.debug_flag)
    
    def connectComponents(self):
        self.dlg.debugButton.clicked.connect(self.switchDebugMode)
        self.dlg.logSaveAs.clicked.connect(self.saveLogAs)
        self.dlg.logClear.clicked.connect(self.myClearLog)
        
    def switchDebugMode(self):
        if self.dlg.debugButton.isChecked():
            utils.debug_flag = True
            utils.info("Debug mode activated")
        else:
            utils.debug_flag = False
            utils.info("Debug mode deactivated")
            
    def saveLogAs(self):
        txt = self.dlg.txtLog.toPlainText()
        fname = qgsUtils.saveFileDialog(self.dlg,msg="Enregistrer le journal sous",filter="*.txt")
        utils.writeFile(fname,txt)
        utils.info("Log saved to file '" + fname + "'")
        
    def myClearLog(self):
        self.dlg.txtLog.clear()

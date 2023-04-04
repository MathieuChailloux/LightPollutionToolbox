# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LightPollutionToolbox
                                 A QGIS plugin
 Light pollution indicators (focus on public lighting)
                              -------------------
        begin                : 2023-04-20
        copyright            : (C) 2023 by Antoine Sensier
        email                : antoine.sensier@inrae.fr
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
import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from .qgis_lib_mc import utils, qgsUtils, log, qgsTreatments, feedbacks, styles
from qgis.core import QgsApplication, QgsProcessingContext, QgsProject, QgsProcessing
from .algs import LightPollutionToolbox_provider
        
class ControllerConnector():

    IND_FIELD_POL = 'indice_pol'
    CLASS_BOUNDS_IND_POL = [0,1,2,3,4,5]
    
    def __init__(self,dlg):

        self.dlg = dlg
      
        self.dlg.pushRunRadianceButton.clicked.connect(self.onPbRunRadianceClicked)
        self.dlg.pushCancelButton.clicked.connect(self.onCancelClicked)
        
        self.dlg.radioButtonImportGrid.clicked.connect(self.onRbImportClicked)
        self.dlg.radioButtonCreateGrid.clicked.connect(self.onRbCreateClicked)
        
    # def initGui(self):
        # self.activateGroupDisplay()
    
        
    def onPbRunRadianceClicked(self):
    
        self.dlg.context.setFeedback(self.dlg.feedback)
        
        out_path = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outFile.filePath():
            out_path = self.dlg.outFile.filePath()

        in_extent_zone = self.dlg.extentFile.filePath()
        in_raster = self.dlg.ImageFile.filePath()
        grid_size = self.dlg.gridSize.value()
        type_grid = self.dlg.gridType.currentIndex()

        if self.dlg.radioButtonImportGrid.isChecked():
            in_grid = self.dlg.gridFile.filePath()
        else:
            in_grid = None
            
        
        self.testRemoveLayer(out_path)
        self.dlg.tabWidget.setCurrentWidget(self.dlg.tabLog)
        
        parameters = { LightPollutionToolbox_provider.StatisticsRadianceGrid.EXTENT_ZONE : in_extent_zone,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.RASTER_INPUT : in_raster,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.GRID_LAYER_INPUT : in_grid,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.DIM_GRID: grid_size,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.TYPE_GRID: type_grid,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.RED_BAND_INPUT:1,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.GREEN_BAND_INPUT:2,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.BLUE_BAND_INPUT:3,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.OUTPUT_STAT : out_path}
        res = qgsTreatments.applyProcessingAlg("LPT","StatisticsRadianceGrid",parameters, onlyOutput=False ,context=self.dlg.context,feedback=self.dlg.feedback)
        
        out_layer = qgsUtils.loadVectorLayer(res['OutputStat'])
        QgsProject.instance().addMapLayer(out_layer)
        styles.setCustomClassesInd_Pol_Category(out_layer, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)                                 

    def onRbImportClicked(self):
        if self.dlg.radioButtonImportGrid.isChecked():
            print('IMPORT GRID')
            self.dlg.stackedGridImportCreate.setCurrentWidget(self.dlg.widgetImportGrid)

    
    def onRbCreateClicked(self):
        if self.dlg.radioButtonCreateGrid.isChecked():
            print('CREATE GRID')
            self.dlg.stackedGridImportCreate.setCurrentWidget(self.dlg.widgetCreateGrid)
            
    
    def onCancelClicked(self):
        self.dlg.close()
    
    
    def testRemoveLayer(self, layer_path):
        # List existing layers ids
        existing_layers_ids = [layer.id() for layer in QgsProject.instance().mapLayers().values()]
        # List existing layers paths
        existing_layers_paths = [layer.dataProvider().dataSourceUri().split('|')[0] for layer in QgsProject.instance().mapLayers().values()]

        if layer_path in existing_layers_paths:
            id_to_remove = existing_layers_ids[existing_layers_paths.index(layer_path)]
            QgsProject.instance().removeMapLayer(id_to_remove)
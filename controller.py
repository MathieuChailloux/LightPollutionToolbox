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
from qgis.core import QgsApplication, QgsProcessingContext, QgsProject, QgsProcessing, QgsProcessingAlgRunnerTask, QgsVectorFileWriter
from .algs import LightPollutionToolbox_provider
from functools import partial
import processing
import time

class ControllerConnector():

    IND_FIELD_POL = 'indice_pol'
    CLASS_BOUNDS_IND_POL = [0,1,2,3,4,5]
    
    RADIANCE = 'Radiance'
    BLUE_EMISSION = 'BlueEmission'
    
    def __init__(self,dlg):

        self.dlg = dlg
        self.dlg.progressBar.setValue(0)
        
        
        # init Radiance interface
        self.dlg.outFileVectorRadiance.setFilter("*.shp;;*.gpkg")
        self.dlg.outFileRasterRadiance.setFilter("*.tif")
        self.dlg.pushRunRadianceButton.clicked.connect(self.onPbRunRadianceClicked)
        self.dlg.pushCancelButton.clicked.connect(self.onCancelClicked)
        self.dlg.radioButtonImportGridRadiance.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonImportGridRadiance, self.dlg.stackedGridImportCreateRadiance, self.dlg.widgetImportGridRadiance))
        self.dlg.radioButtonCreateGridRadiance.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonCreateGridRadiance, self.dlg.stackedGridImportCreateRadiance, self.dlg.widgetCreateGridRadiance))
        self.dlg.radioButtonImportGridRadiance.click()
        
        # init Blue emission interface
        self.dlg.outFileVectorBlue.setFilter("*.shp;;*.gpkg")
        self.dlg.pushRunBlueEmissionButton.clicked.connect(self.onPbRunBlueEmissionClicked)
        self.dlg.pushCancelButton.clicked.connect(self.onCancelClicked)
        self.dlg.radioButtonImportGridBlue.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonImportGridBlue, self.dlg.stackedGridImportCreateBlue, self.dlg.widgetImportGridBlue))
        self.dlg.radioButtonCreateGridBlue.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonCreateGridBlue, self.dlg.stackedGridImportCreateBlue, self.dlg.widgetCreateGridBlue))
        self.dlg.radioButtonImportGridBlue.click()
        
        self.task = None
        self.taskRun = False  
        
    # def initGui(self):
        # self.activateGroupDisplay()
    
        
    def onPbRunRadianceClicked(self):
        
        self.dlg.pushRunRadianceButton.setEnabled(False)
        
        self.dlg.context.setFeedback(self.dlg.feedback)
        
        out_path_vector = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outFileVectorRadiance.filePath():
            out_path_vector = self.dlg.outFileVectorRadiance.filePath()
            
        out_path_raster = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outFileRasterRadiance.filePath():
            out_path_raster = self.dlg.outFileRasterRadiance.filePath()

        in_extent_zone = self.dlg.extentFileRadiance.filePath()
        in_raster = self.dlg.ImageFileRadiance.filePath()
        grid_size = self.dlg.gridSizeRadiance.value()
        type_grid = self.dlg.gridTypeRadiance.currentIndex()
        if self.dlg.radioButtonImportGridRadiance.isChecked():
            in_grid = self.dlg.gridFileRadiance.filePath()
            if not in_grid :
                self.dlg.radioButtonCreateGridRadiance.click()
        else:
            in_grid = None           
        
        self.testRemoveLayer(out_path_vector)
        self.testRemoveLayer(out_path_raster)
        
        self.taskRun = True
        parameters = { LightPollutionToolbox_provider.StatisticsRadianceGrid.EXTENT_ZONE : in_extent_zone,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.RASTER_INPUT : in_raster,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.GRID_LAYER_INPUT : in_grid,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.DIM_GRID: grid_size,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.TYPE_GRID: type_grid,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.RED_BAND_INPUT:1,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.GREEN_BAND_INPUT:2,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.BLUE_BAND_INPUT:3,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.OUTPUT_STAT : out_path_vector,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.OUTPUT_RASTER_RADIANCE : out_path_raster}
        
        alg = QgsApplication.processingRegistry().algorithmById("LPT:StatisticsRadianceGrid")
        self.task = QgsProcessingAlgRunnerTask(alg, parameters, self.dlg.context, self.dlg.feedback)
        self.task.executed.connect(partial(self.task_finished, self.dlg.context, self.RADIANCE))
        QgsApplication.taskManager().addTask(self.task)

    
    def onPbRunBlueEmissionClicked(self):
    
        self.dlg.pushRunBlueEmissionButton.setEnabled(False)
            
        self.dlg.context.setFeedback(self.dlg.feedback)
        
        out_path_vector = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outFileVectorBlue.filePath():
            out_path_vector = self.dlg.outFileVectorBlue.filePath()
            
        in_extent_zone = self.dlg.extentFileBlue.filePath()
        in_raster = self.dlg.ImageFileBlue.filePath()
        grid_size = self.dlg.gridSizeBlue.value()
        type_grid = self.dlg.gridTypeBlue.currentIndex()
        if self.dlg.radioButtonImportGridBlue.isChecked():
            in_grid = self.dlg.gridFileBlue.filePath()
            if not in_grid :
                self.dlg.radioButtonCreateGridBlue.click()
        else:
            in_grid = None
        
        self.testRemoveLayer(out_path_vector)
        
        self.taskRun = True
        parameters = { LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.EXTENT_ZONE : in_extent_zone,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.RASTER_INPUT : in_raster,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.GRID_LAYER_INPUT : in_grid,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.DIM_GRID_CALC: grid_size,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.TYPE_GRID: type_grid,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.RED_BAND_INPUT:1,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.GREEN_BAND_INPUT:2,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.BLUE_BAND_INPUT:3,
                       LightPollutionToolbox_provider.StatisticsBlueEmissionGrid.OUTPUT_STAT_CALC : out_path_vector}
        
        alg = QgsApplication.processingRegistry().algorithmById("LPT:StatisticsBlueEmissionGrid")
        self.task = QgsProcessingAlgRunnerTask(alg, parameters, self.dlg.context, self.dlg.feedback)
        self.task.executed.connect(partial(self.task_finished, self.dlg.context, self.BLUE_EMISSION))
        QgsApplication.taskManager().addTask(self.task)
    
    def onRbImportCreateClicked(self, radioButton, stackedGrid, widgetGrid):
        if radioButton.isChecked():
            stackedGrid.setCurrentWidget(widgetGrid)

    
    def onCancelClicked(self):
        if self.taskRun:
            self.task.cancel()
            # self.taskRun = False           
        else:
            self.dlg.pushRunBlueEmissionButton.setEnabled(True)
            self.dlg.pushRunRadianceButton.setEnabled(True)
            self.dlg.close()
         
    
    def testRemoveLayer(self, layer_path):
        # Remove layer if existe
        # todo : problème avec shapefile, se supprime mal si ouvert dans QGIS
        # List existing layers ids
        existing_layers_ids = [layer.id() for layer in QgsProject.instance().mapLayers().values()]
        # List existing layers paths
        existing_layers_paths = [layer.dataProvider().dataSourceUri().split('|')[0] for layer in QgsProject.instance().mapLayers().values()]

        if layer_path in existing_layers_paths:
            id_to_remove = existing_layers_ids[existing_layers_paths.index(layer_path)]
            QgsProject.instance().removeMapLayer(id_to_remove)
            if layer_path.endswith(".shp"):
                print(QgsVectorFileWriter.deleteShapeFile(layer_path))
            
    
    def task_finished(self, context, indicator, successful, results):
        if self.task.isCanceled():
            self.dlg.progressBar.setValue(0)
            self.dlg.feedback.pushInfo("Treatement canceled")
            self.dlg.tabWidget.setCurrentWidget(self.dlg.tabLog)
        elif successful:
            for outputkey in results.keys():
                if ".tif" in results[outputkey]:
                    output_layer = qgsUtils.loadRasterLayer(results[outputkey])
                else:
                    output_layer = qgsUtils.loadVectorLayer(results[outputkey])
                    
                if output_layer.isValid():
                    QgsProject.instance().addMapLayer(output_layer)
                    
                if indicator == self.RADIANCE:
                    if ".tif" not in results[outputkey]:
                        styles.setCustomClassesInd_Pol_Category(output_layer, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)
                elif indicator == self.BLUE_EMISSION:
                    if ".tif" not in results[outputkey]:
                        styles.setCustomClassesInd_Pol_Category(output_layer, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)
        else: # FAIL
             self.dlg.feedback.pushInfo("Treatement failed")
             self.dlg.tabWidget.setCurrentWidget(self.dlg.tabLog)
        self.dlg.pushRunRadianceButton.setEnabled(True)
        self.dlg.pushRunBlueEmissionButton.setEnabled(True)
        self.taskRun = False

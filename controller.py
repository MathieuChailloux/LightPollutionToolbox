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
from qgis.core import QgsApplication, QgsProcessingContext, QgsProject, QgsProcessing, QgsProcessingAlgRunnerTask, QgsVectorFileWriter, QgsMapLayerProxyModel
from .algs import LightPollutionToolbox_provider
from functools import partial
import processing
import time

class ControllerConnector():

    IND_FIELD_POL = 'indice_pol'
    CLASS_BOUNDS_IND_POL = [0,1,2,3,4,5]
    
    RADIANCE = 'Radiance'
    BLUE_EMISSION = 'BlueEmission'
    NB_LIGHT_SOURCES = 'NbLightSources'
    MNS = 'Mns'
    FIELD_STYLE = '_mean'
    LAST_BOUNDS_VALUE = 50
    
    def __init__(self,dlg):
        self.dlg = dlg
        self.dlg.progressBar.setValue(0)
        
        self.dlg.pushCancelButton.clicked.connect(self.onCancelClicked)
        
        # init Radiance interface
        self.dlg.outFileVectorRadiance.setFilter("*.shp;;*.gpkg")
        self.dlg.outFileRasterRadiance.setFilter("*.tif")
        self.dlg.pushRunRadianceButton.clicked.connect(self.onPbRunRadianceClicked)
        self.dlg.radioButtonImportGridRadiance.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonImportGridRadiance, self.dlg.stackedGridImportCreateRadiance, self.dlg.widgetImportGridRadiance))
        self.dlg.radioButtonCreateGridRadiance.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonCreateGridRadiance, self.dlg.stackedGridImportCreateRadiance, self.dlg.widgetCreateGridRadiance))
        self.dlg.radioButtonImportGridRadiance.click()
        
        # init Blue emission interface
        self.dlg.outFileVectorBlue.setFilter("*.shp;;*.gpkg")
        self.dlg.pushRunBlueEmissionButton.clicked.connect(self.onPbRunBlueEmissionClicked)
        self.dlg.radioButtonImportGridBlue.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonImportGridBlue, self.dlg.stackedGridImportCreateBlue, self.dlg.widgetImportGridBlue))
        self.dlg.radioButtonCreateGridBlue.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonCreateGridBlue, self.dlg.stackedGridImportCreateBlue, self.dlg.widgetCreateGridBlue))
        self.dlg.radioButtonImportGridBlue.click()
        
        # init calcul MNS
        self.dlg.outputRasterMNS.setFilter("*.tif")
        self.dlg.outputRasterBatiVege.setFilter("*.tif")
        self.dlg.pushRunMNS.clicked.connect(self.onPbRunMNSClicked)
        self.dlg.extentFileMNS.clicked.connect(partial(self.select_file, "vector", self.dlg.mMapLayerComboBoxExtentMNS))
        self.dlg.mntFile.clicked.connect(partial(self.select_file, "raster", self.dlg.mMapLayerComboBoxMNT))
        self.dlg.buildingsFile.clicked.connect(partial(self.select_file, "vector", self.dlg.mMapLayerComboBoxBuildings))
        self.dlg.vegetationFile.clicked.connect(partial(self.select_file, "vector", self.dlg.mMapLayerComboBoxVegetation))
        self.dlg.mMapLayerComboBoxExtentMNS.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.mMapLayerComboBoxMNT.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.dlg.mMapLayerComboBoxBuildings.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.mMapLayerComboBoxVegetation.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.mMapLayerComboBoxBuildings.layerChanged.connect(partial(self.setInLayerFromCombo, self.dlg.mMapLayerComboBoxBuildings, self.dlg.mFieldComboBoxBuildings))
        self.dlg.mMapLayerComboBoxVegetation.layerChanged.connect(partial(self.setInLayerFromCombo, self.dlg.mMapLayerComboBoxVegetation, self.dlg.mFieldComboBoxVegetation))
        
        
        # init Number of light visibility
        self.dlg.outputFileNbLight.setFilter("*.shp;;*.gpkg")
        self.dlg.pushRunNbLightButton.clicked.connect(self.onPbRunNbLightClicked)
        self.dlg.extentFileNbLight.clicked.connect(partial(self.select_file, "vector", self.dlg.mMapLayerComboBoxExtentNbLight))
        self.dlg.viewshedFile.clicked.connect(partial(self.select_file, "raster", self.dlg.mMapLayerComboBoxViewshedResult))
        self.dlg.rasterBatiVegeFile.clicked.connect(partial(self.select_file, "raster", self.dlg.mMapLayerComboBoxRasterBatiVege))
        self.dlg.mMapLayerComboBoxExtentNbLight.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.mMapLayerComboBoxViewshedResult.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.dlg.mMapLayerComboBoxRasterBatiVege.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.dlg.radioButtonImportGridNbLight.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonImportGridNbLight, self.dlg.stackedGridImportCreateNbLight, self.dlg.widgetImportGridNbLight))
        self.dlg.radioButtonCreateGridNbLight.clicked.connect(partial(self.onRbImportCreateClicked, self.dlg.radioButtonCreateGridNbLight, self.dlg.stackedGridImportCreateNbLight, self.dlg.widgetCreateGridNbLight))
        self.dlg.radioButtonImportGridNbLight.click()
        
        self.task = None
        self.taskRun = False  
        
    # def initGui(self):
        # self.activateGroupDisplay()
    
        
    def onPbRunRadianceClicked(self):
        self.togglePushButton(False)
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
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.RED_BAND_INPUT:1, # TODO ADD to interface ?
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.GREEN_BAND_INPUT:2,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.BLUE_BAND_INPUT:3,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.OUTPUT_STAT : out_path_vector,
                       LightPollutionToolbox_provider.StatisticsRadianceGrid.OUTPUT_RASTER_RADIANCE : out_path_raster}
        
        alg = QgsApplication.processingRegistry().algorithmById("LPT:StatisticsRadianceGrid")
        self.task = QgsProcessingAlgRunnerTask(alg, parameters, self.dlg.context, self.dlg.feedback)
        self.task.executed.connect(partial(self.task_finished, self.dlg.context, self.RADIANCE))
        QgsApplication.taskManager().addTask(self.task)

    
    def onPbRunBlueEmissionClicked(self):
        self.togglePushButton(False)
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


    def onPbRunMNSClicked(self):
        self.togglePushButton(False)
        self.dlg.context.setFeedback(self.dlg.feedback)
        
        out_path_raster_MNS = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outputRasterMNS.filePath():
            out_path_raster_MNS = self.dlg.outputRasterMNS.filePath()
        out_path_raster_bati_vege = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outputRasterBatiVege.filePath():
            out_path_raster_bati_vege = self.dlg.outputRasterBatiVege.filePath()    

        in_extent_zone = self.dlg.mMapLayerComboBoxExtentMNS.currentLayer()
        in_raster_mnt = self.dlg.mMapLayerComboBoxMNT.currentLayer()
        
        buffer_radius = self.dlg.RadiusMNSValue.value()
        in_buildings = self.dlg.mMapLayerComboBoxBuildings.currentLayer()
        heigt_builings_field = self.dlg.mFieldComboBoxBuildings.currentField()
        in_vegetation = self.dlg.mMapLayerComboBoxVegetation.currentLayer()
        heigt_vegetation_field = self.dlg.mFieldComboBoxVegetation.currentField()
        default_height_vegetation = self.dlg.vegetationHeightValue.value()
        
        self.testRemoveLayer(out_path_raster_MNS)
        self.testRemoveLayer(out_path_raster_bati_vege)
        self.taskRun = True
        parameters = { LightPollutionToolbox_provider.CalculMNS.EXTENT_ZONE : in_extent_zone,
                       LightPollutionToolbox_provider.CalculMNS.RASTER_MNT_INPUT : in_raster_mnt,
                       LightPollutionToolbox_provider.CalculMNS.BATI_INPUT : in_buildings,
                       LightPollutionToolbox_provider.CalculMNS.BUFFER_RADIUS : buffer_radius,
                       LightPollutionToolbox_provider.CalculMNS.HEIGHT_FIELD_BATI : heigt_builings_field,
                       LightPollutionToolbox_provider.CalculMNS.VEGETATION_INPUT : in_vegetation,
                       LightPollutionToolbox_provider.CalculMNS.HEIGHT_FIELD_VEGETATION : heigt_vegetation_field,
                       LightPollutionToolbox_provider.CalculMNS.DEFAULT_HEIGHT_VEGETATION : default_height_vegetation,
                       LightPollutionToolbox_provider.CalculMNS.OUTPUT_RASTER_MNS : out_path_raster_MNS,
                       LightPollutionToolbox_provider.CalculMNS.OUTPUT_RASTER_BATI : out_path_raster_bati_vege}
        
        alg = QgsApplication.processingRegistry().algorithmById("LPT:CalculMNS")
        self.task = QgsProcessingAlgRunnerTask(alg, parameters, self.dlg.context, self.dlg.feedback)
        self.task.executed.connect(partial(self.task_finished, self.dlg.context, self.MNS))
        QgsApplication.taskManager().addTask(self.task)
        
        
    def onPbRunNbLightClicked(self):
        self.togglePushButton(False)
        self.dlg.context.setFeedback(self.dlg.feedback)
        
        out_path_vector = QgsProcessing.TEMPORARY_OUTPUT
        if self.dlg.outputFileNbLight.filePath():
            out_path_vector = self.dlg.outputFileNbLight.filePath()
            
        in_extent_zone = self.dlg.mMapLayerComboBoxExtentNbLight.currentLayer()
        in_raster_viewshed = self.dlg.mMapLayerComboBoxViewshedResult.currentLayer()
        in_raster_bati_vege = self.dlg.mMapLayerComboBoxRasterBatiVege.currentLayer()
        self.LAST_BOUNDS_VALUE = self.dlg.lastBoundsValue.value()
        mask_height = self.dlg.maskHeightValue.value()
        grid_size = self.dlg.gridSizeNbLight.value()
        type_grid = self.dlg.gridTypeNbLight.currentIndex()
        if self.dlg.radioButtonImportGridNbLight.isChecked():
            in_grid = self.dlg.gridFileNbLight.filePath()
            if not in_grid :
                self.dlg.radioButtonCreateGridNbLight.click()
        else:
            in_grid = None
        
        self.testRemoveLayer(out_path_vector)
        self.taskRun = True
        parameters = { LightPollutionToolbox_provider.AnalyseVisibilityLightSources.EXTENT_ZONE : in_extent_zone,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.VIEWSHED_INPUT : in_raster_viewshed,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.RASTER_BATI_INPUT : in_raster_bati_vege,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.GRID_LAYER_INPUT : in_grid,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.DIM_GRID: grid_size,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.TYPE_GRID: type_grid,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.MASK_HEIGHT: mask_height,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.LAST_BOUNDS: self.LAST_BOUNDS_VALUE,
                       LightPollutionToolbox_provider.AnalyseVisibilityLightSources.OUTPUT_NB_SRC_VIS : out_path_vector}
        
        alg = QgsApplication.processingRegistry().algorithmById("LPT:AnalyseVisibilityLightSources")
        self.task = QgsProcessingAlgRunnerTask(alg, parameters, self.dlg.context, self.dlg.feedback)
        self.task.executed.connect(partial(self.task_finished, self.dlg.context, self.NB_LIGHT_SOURCES))
        QgsApplication.taskManager().addTask(self.task)
   
   
    def onRbImportCreateClicked(self, radioButton, stackedGrid, widgetGrid):
        if radioButton.isChecked():
            stackedGrid.setCurrentWidget(widgetGrid)

    
    def onCancelClicked(self):
        if self.taskRun:
            self.task.cancel()
            # self.taskRun = False           
        else:
            self.togglePushButton(True)
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
                QgsVectorFileWriter.deleteShapeFile(layer_path)
            
            
    def select_file(self, fileType, mapLayerComboBox):
        qfd = QtWidgets.QFileDialog()
        if fileType == "raster":
            filt = self.dlg.tr("Raster files(*.tif)")
        elif fileType == "vector":
            filt = self.dlg.tr("Vector files(*.shp)")
            
        title = self.dlg.tr("Select a "+fileType+" file")
        f, _ = QtWidgets.QFileDialog.getOpenFileName(qfd, title, ".", filt)
        if f != "" and f is not None:
            if fileType == "raster":
                layer = qgsUtils.loadRasterLayer(f)
            elif fileType == "vector":
                layer = qgsUtils.loadVectorLayer(f)
            QgsProject.instance().addMapLayer(layer)
            mapLayerComboBox.setLayer(layer)
    
    
    def setInLayerFromCombo(self, comboboxLayer, comboboxField):
        utils.debug("setInLayerFromCombo")
        layer = comboboxLayer.currentLayer()
        utils.debug(str(layer.__class__.__name__))
        if layer:
            path = qgsUtils.pathOfLayer(layer)
            comboboxField.setLayer(layer)
        else:
            utils.warn("Could not load selection in layer")
            
            
    def togglePushButton(self, activate):
        self.dlg.pushRunRadianceButton.setEnabled(activate)
        self.dlg.pushRunBlueEmissionButton.setEnabled(activate)
        self.dlg.pushRunMNS.setEnabled(activate)
        self.dlg.pushRunViewshed.setEnabled(activate)
        self.dlg.pushRunNbLightButton.setEnabled(activate)
     
     
    def task_finished(self, context, indicator, successful, results):
        if self.task.isCanceled():
            self.dlg.progressBar.setValue(0)
            self.dlg.feedback.pushInfo("Treatement canceled")
            self.dlg.tabWidget.setCurrentWidget(self.dlg.tabLog)
        elif bool(results): # elif successful:
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
                elif indicator == self.NB_LIGHT_SOURCES:
                    if ".tif" not in results[outputkey]:
                        bounds = styles.getQuantileBounds(output_layer, self.FIELD_STYLE, lastBounds=self.LAST_BOUNDS_VALUE)
                        styles.setCustomClassesInd_Pol_Graduate(output_layer, self.FIELD_STYLE, bounds)
        else: # FAIL
             self.dlg.feedback.pushInfo("Treatement failed")
             self.dlg.tabWidget.setCurrentWidget(self.dlg.tabLog)
        self.togglePushButton(True)
        self.task.disconnect()
        self.taskRun = False

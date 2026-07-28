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
    Useful functions to perform base operation on QGIS interface and data types.
"""

import os
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsField,
    QgsLayerTreeNode,
    QgsMapLayer,
    QgsProcessingAlgorithm,
    QgsProcessingParameterDefinition,
    QgsProcessingUtils,
    QgsProject,
    QgsRasterBandStats,
    QgsRasterLayer,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtWidgets import QFileDialog

from . import utils


if os.environ.get("GTIFF_COPT") is not None:
    GTIFF_COPT = os.environ["GTIFF_COPT"].split()
else:
    GTIFF_COPT = ["BIGTIFF=IF_SAFER", "COMPRESS=LZW", "NUM_THREADS=ALL_CPUS"]

# Delete raster file and associated xml file
def removeRaster(path):
    if isLayerLoaded(path):
        utils.user_error("Layer " + str(path) + " is already loaded in QGIS, please remove it")
    utils.removeFile(path)
    aux_name = path + ".aux.xml"
    utils.removeFile(aux_name)

# Returns path from QgsMapLayer
def pathOfLayer(l):
    uri = l.dataProvider().dataSourceUri()
    if l.type() == QgsMapLayer.VectorLayer and '|' in uri:
        path = uri[:uri.rfind('|')]
    else:
        path = uri
    return path

def layerNameOfPath(p):
    bn = os.path.basename(p)
    res = os.path.splitext(bn)[0]
    return res

def getLayerByFilename(fname):
    map_layers = QgsProject.instance().mapLayers().values()
    fname_parts = Path(fname.lower()).parts
    utils.debug("fname_parts : " + str(fname_parts))
    for layer in map_layers:
        # utils.debug("layer : " + str(layer.name()))
        layer_path = pathOfLayer(layer)
        path_parts = Path(layer_path.lower()).parts
        # utils.debug("path_parts : " + str(path_parts))
        if fname_parts == path_parts:
            return layer
    else:
        return None

def isLayerLoaded(fname):
    return (getLayerByFilename(fname) != None)

def normalizeEncoding(layer):
    path = pathOfLayer(layer)
    extension = os.path.splitext(path)[1].lower()
    utils.debug("extension = " + str(extension))
    utils.debug("system = " + str(utils.platform_sys))
    if extension == ".shp" and (utils.platform_sys in ["Linux","Darwin"]):
        layer.dataProvider().setEncoding('Latin-1')
    elif extension == ".shp":
        layer.dataProvider().setEncoding('System')
    elif extension == ".gpkg":
        layer.dataProvider().setEncoding('UTF-8')

def loadLayerInQGIS(layer,groupName=None):
    if groupName:
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(groupName)
        if not group:
            group = root.addGroup(groupName)
        QgsProject.instance().addMapLayer(layer,False)
        group.addLayer(layer)
        # group.insertChildNode(0,layer)
    else:
        QgsProject.instance().addMapLayer(layer,True)

# Opens vector layer from path.
# If loadProject is True, layer is added to QGIS project
def loadVectorLayer(fname,loadProject=False,normalize=False,groupName=None,
        checkValidity=True):
    utils.debug("loadVectorLayer " + str(fname))
    utils.checkFileExists(fname)
    if isLayerLoaded(fname):
       return getLayerByFilename(fname)
    layer = QgsVectorLayer(fname, layerNameOfPath(fname), "ogr")
    if not layer:
        utils.user_error("Could not load vector layer '" + fname + "'")
    if checkValidity and not layer.isValid():
        utils.user_error("Invalid vector layer '" + fname + "'")
    if normalize:
        normalizeEncoding(layer)
    if loadProject:
        loadLayerInQGIS(layer,groupName=groupName)
    return layer

# Opens raster layer from path.
# If loadProject is True, layer is added to QGIS project
def loadRasterLayer(fname,loadProject=False,groupName=None):
    utils.debug("loadRasterLayer " + str(fname))
    utils.checkFileExists(fname)
    if isLayerLoaded(fname):
        return getLayerByFilename(fname)
    rlayer = QgsRasterLayer(fname, layerNameOfPath(fname))
    if not rlayer.isValid():
        utils.user_error("Invalid raster layer '" + fname + "'")
    if loadProject:
        loadLayerInQGIS(rlayer,groupName=groupName)
    return rlayer

def removeGroupR(root,groupName):
    #print("removeGroupR " + str(root.name()))
    children = root.children()
    for c in children:
        if c.nodeType() ==  QgsLayerTreeNode.NodeGroup:
            if c.name() == groupName:
                root.removeChildNode(c)    
            else:
                removeGroupR(c,groupName)

# Find all groups
def findGroupsAll(root=None):
    if root is None:
        root = QgsProject.instance().layerTreeRoot()
    groups = root.findGroups()
    for c in root.children():
        if c.nodeType() ==  QgsLayerTreeNode.NodeGroup:
            groups += findGroupsAll(c)
    return groups

# LAYER PARAMETERS

# Returns geometry type string (e.g. 'MultiPolygon')
def getLayerGeomStr(layer):
    return QgsWkbTypes.displayString(layer.wkbType())

# Checks if geometry is multipart
def isMultipartLayer(layer):
    wkb_type = layer.wkbType()
    is_multi = QgsWkbTypes.isMultiType(wkb_type)
    return is_multi

def createOrUpdateField(in_layer,func,out_field):
    if out_field not in in_layer.fields().names():
        field = QgsField(out_field, QVariant.Double)
        in_layer.dataProvider().addAttributes([field])
        in_layer.updateFields()
    
    in_layer.startEditing()    
    for f in in_layer.getFeatures():
        f[out_field] = func(f)
        in_layer.updateFeature(f)
    in_layer.commitChanges()

def transformBoundingBox(in_rect,in_crs,out_crs):
    transformator = QgsCoordinateTransform(in_crs,out_crs,QgsProject.instance())
    out_rect = transformator.transformBoundingBox(in_rect)
    return out_rect


""" Raster utilities """

def getRasterStats(layer):
    pr = layer.dataProvider()
    stats = pr.bandStatistics(1,stats=QgsRasterBandStats.All)
    return stats

def getRasterMinMax(layer):
    stats = getRasterStats(layer)
    min, max = stats.minimumValue, stats.maximumValue
    return (min, max)

def getRastersMinMax(layers):
    if not layers:
        utils.internal_error("No layers selected")
    min, max = getRasterMinMax(layers[0])
    for l in layers:
        curr_min, curr_max = getRasterMinMax(l)
        if curr_min < min:
            min = curr_min
        if curr_max > max:
            max = curr_max
    return (min, max)


def getRasterMinMedMax(layer):
    stats = getRasterStats(layer)
    min, max = stats.minimumValue, stats.maximumValue
    range = max - min
    half_range = range//2
    med = min + half_range
    return (min,med,max)

def checkProjectionUnit(layer):
    if layer is not None:
        if layer.crs().mapUnits() != 0: # QgsUnitTypes.encodeUnit(0) == "meters"
            utils.internal_error("The layer "+layer.name()+" has a projection in "+layer.crs().authid()+", with "+QgsUnitTypes.encodeUnit(layer.crs().mapUnits())+" unit, it must be in meter unit (like EPSG:2154).")


""" UI utilities """    

# Opens file dialog in open mode
def openFileDialog(parent,msg="",filter=""):
    fname, filter = QFileDialog.getOpenFileName(parent,
        caption=msg,
        directory=utils.dialog_base_dir,
        filter=filter)
    return fname

# Opens file dialog in save mode
def saveFileDialog(parent,msg="",filter=""):
    fname, filter = QFileDialog.getSaveFileName(parent,
                                                caption=msg,
                                                directory=utils.dialog_base_dir,
                                                filter=filter)
    return fname
        

""" Processing utlities """

def mkTmpPath(fname):
    return QgsProcessingUtils.generateTempFilename(fname)

# Base algorithm
class BaseProcessingAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    def __init__(self):
        super().__init__()
    #def tr(self, string):
    #    return QCoreApplication.translate(self.__class__.__name__, string)
    def tr(self, string, context=''):
        if context == '':
            context = self.__class__.__name__
        return QCoreApplication.translate(context, string)
    def name(self):
        return self.ALG_NAME
    def createInstance(self):
        return type(self)()
    def addAdvancedParam(self,param):
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
    def mkTmpPath(self,fname):
        return QgsProcessingUtils.generateTempFilename(fname)
    def parameterAsSourceLayer(self,parameters,paramName,context,feedback=None):
        feedback = feedback if feedback else self.feedback
        source = self.parameterAsSource(parameters,paramName,context)
        if source:
            layer = source.materialize(QgsFeatureRequest(),feedback=feedback)
        else:
            layer = None
        return source, layer


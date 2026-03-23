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

import os, shutil
from pathlib import Path
import numpy as np

try:
    from osgeo import gdal
except ImportError:
    import gdal

import qgis
from qgis.gui import *
from qgis.core import *
from PyQt5.QtCore import QCoreApplication, QVariant, pyqtSignal
from PyQt5.QtWidgets import QFileDialog

from . import utils


if os.environ.get("GTIFF_COPT") is not None:
    GTIFF_COPT = os.environ["GTIFF_COPT"].split()
else:
    GTIFF_COPT = ["BIGTIFF=IF_SAFER", "COMPRESS=LZW", "NUM_THREADS=ALL_CPUS"]


def typeIsInteger(t):
    return (t == QVariant.Int
            or t == QVariant.UInt
            or t == QVariant.LongLong
            or t == QVariant.ULongLong)
            
def typeIsFloat(t):
    return (t == QVariant.Double)
    
def typeIsNumeric(t):
    return (typeIsInteger(t) or typeIsFloat(t))

def qgisTypeIsInteger(t):
    int_types = [Qgis.Byte, Qgis.UInt16, Qgis.Int16, Qgis.UInt32, Qgis.Int32]
    return (t in int_types)
    
def isVectorLayer(layer):
    return layer.type() == QgsMapLayer.VectorLayer
    
def isRasterLayer(layer):
    return layer.type() == QgsMapLayer.RasterLayer
    
def removeFolder(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    
# Delete raster file and associated xml file
def removeRaster(path):
    if isLayerLoaded(path):
        utils.user_error("Layer " + str(path) + " is already loaded in QGIS, please remove it")
    utils.removeFile(path)
    aux_name = path + ".aux.xml"
    utils.removeFile(aux_name)
            
def removeVectorLayer(path):
    if isLayerLoaded(path):
        utils.user_error("Layer " + str(path) + " is already loaded in QGIS, please remove it")
    utils.removeFile(path)
    
# Returns path from QgsMapLayer
def pathOfLayer(l):
    uri = l.dataProvider().dataSourceUri()
    if l.type() == QgsMapLayer.VectorLayer and '|' in uri:
        path = uri[:uri.rfind('|')]
    else:
        path = uri
    #utils.debug("pathOfLayer uri " + str(uri))
    #utils.debug("pathOfLayer path " + str(path))
    return path
      
def layerNameOfPath(p):
    bn = os.path.basename(p)
    res = os.path.splitext(bn)[0]
    return res
    
def getVectorFilters():
    return QgsProviderRegistry.instance().fileVectorFilters()
    
def getRasterFilters():
    return QgsProviderRegistry.instance().fileRasterFilters()
           
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

# Opens layer from path.
# If loadProject is True, layer is added to QGIS project
#def loadLayerOld(fname,loadProject=False):
#    try:
#        return (loadVectorLayer(fname,loadProject))
#    except utils.CustomException:
#        try:
#            return (loadRasterLayer(fname,loadProject))
#        except utils.CustomException:
#            utils.user_error("Could not load layer '" + fname + "'")
            
def loadVectorLayerNoError(fname):
    layer = QgsVectorLayer(fname, layerNameOfPath(fname), "ogr")
    if not layer:
        utils.debug("Could not load vector layer '" + fname + "'")
        return None
    if not layer.isValid():
        utils.debug("Invalid vector layer '" + fname + "'")
        return None
    normalizeEncoding(layer)
    return layer
    
def loadRasterLayerNoError(fname):
    layer = QgsRasterLayer(fname, layerNameOfPath(fname))
    if not layer:
        utils.debug("Could not load raster layer '" + fname + "'")
        return None
    if not layer.isValid():
        utils.debug("Invalid raster layer '" + fname + "'")
        return None
    return layer
    
def loadLayer(fname,loadProject=False,groupName=None):
    utils.debug("loadLayer " + str(fname))
    if isLayerLoaded(fname):
        return getLayerByFilename(fname)
    layer = loadVectorLayerNoError(fname)
    if layer is None:
        layer = loadRasterLayerNoError(fname)
    if layer is None:
        utils.user_error("Could not load layer '" + fname + "'")
    if loadProject:
        loadLayerInQGIS(layer,groupName=groupName)
    return layer
    
# def loadLayerNone(fname,loadProject=False):
    # utils.debug("loadLayer " + str(fname))
    # if not fname:
        # return None
    # if not os.path.isfile(fname):
        # return None
    # return loadLayer(fname,loadProject=loadProject)
            
#def loadLayerGetTypeOld(fname,loadProject=False):
#    utils.checkFileExists(fname)
#    try:
#        layer = loadVectorLayer(fname,loadProject)
#        type = 'Vector'
#        return (layer, type)
#    except utils.CustomException:
#        try:
#            layer = loadRasterLayer(fname,loadProject)
#            type = 'Raster'
#            return (layer, type)
#        except utils.CustomException:
#            utils.user_error("Could not load layer '" + fname + "'")
    
def loadLayerGetType(fname,loadProject=False,groupName=None):
    utils.debug("loadLayerGetType " + str(fname))
    layer = loadVectorLayerNoError(fname)
    type = 'Vector'
    if layer is None:
        layer = loadRasterLayerNoError(fname)
        type = 'Raster'
    if layer is None:
        utils.user_error("Could not load layer '" + fname + "'")
    if loadProject:
        loadLayerInQGIS(layer,groupName=groupName)
    return (layer, type)
    
# Retrieve layer loaded in QGIS project from name
def getLoadedLayerByName(name):
    utils.debug("Layers = " + str([l.name() for l in QgsProject.instance().mapLayers().values()]))
    layers = QgsProject.instance().mapLayersByName(name)
    nb_layers = len(layers)
    if nb_layers == 0:
        utils.warn("No layer named '" + name + "' found")
        return None
    elif nb_layers > 1:
        utils.user_error("Several layers named '" + name + "' found")
    else:
        return layers[0]
    
def removeLayer(layer):
    inst = QgsProject.instance()
    inst.removeMapLayers( [layer.id()] )
def removeLayerFromPath(layerPath):
    utils.debug("removeLayerFromPath" + str(layerPath))
    layer = getLayerByFilename(layerPath)
    utils.debug("layer ZZ {}".format(layer))
    if layer:
        removeLayer(layer)
    
def removeGroupOld(groupName):
    root = QgsProject.instance().layerTreeRoot()
    groupNode = root.findGroup(groupName)
    if groupNode:
        root.removeChildNode(groupNode)    
def removeGroupR(root,groupName):
    #print("removeGroupR " + str(root.name()))
    children = root.children()
    for c in children:
        if c.nodeType() ==  QgsLayerTreeNode.NodeGroup:
            if c.name() == groupName:
                root.removeChildNode(c)    
            else:
                removeGroupR(c,groupName)
    
def removeGroups(groupName):
    root = QgsProject.instance().layerTreeRoot()
    removeGroupR(root,groupName)
    
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

# Returns CRS code in lowercase (e.g. 'epsg:2154')
def getLayerCrsStr(layer):
    return str(layer.crs().authid().lower())
    
# Returns geometry type string (e.g. 'MultiPolygon')
def getLayerGeomStr(layer):
    return QgsWkbTypes.displayString(layer.wkbType())
    
# Returns simple geometry type string (e.g. 'Polygon', 'Line', 'Point')
def getLayerSimpleGeomStr(layer):
    type = layer.wkbType()
    geom_type = QgsWkbTypes.geometryType(type)
    return QgsWkbTypes.geometryDisplayString(geom_type)
    
# Checks if geometry is multipart
def isMultipartLayer(layer):
    wkb_type = layer.wkbType()
    is_multi = QgsWkbTypes.isMultiType(wkb_type)
    return is_multi
    
def hasPolygonGeometry(layer):
    geomType = layer.geometryType()
    return geomType == QgsWkbTypes.PolygonGeometry 
    
# Returns smallest unisgned type (GDAL type) in which max_val can be represented
def getGDALUnsignedType(max_val):
    if max_val < 256:
        return gdal.GDT_Byte
    elif max_val < 65536:
        return gdal.GDT_UInt16
    else:
        return gdal.GDT_UInt32

# Returns smallest unisgned type (GDAL type) in which max_val can be represented
def getGDALUnsignedTypeAndND(max_val):
    if max_val < 255:
        return gdal.GDT_Byte, 255
    elif max_val < 65535:
        return gdal.GDT_UInt16, 65535
    else:
        return gdal.GDT_UInt32, sys.maxsize
    
# Returns smallest unisgned type (GDAL type) in which max_val can be represented
# def getGDALTypeAndND(max_val):
    # if max_val < 255:
        # return gdal.GDT_Byte, 255
    # elif max_val < 65535:
        # return gdal.GDT_UInt16, 65535
    # else:
        # return gdal.GDT_UInt32, sys.maxsize
        
# Returns maximum value that can be represented in input unsigned type (QGIS type)
def getQGISTypeMaxVal(type):
    unsigned = { Qgis.Byte : 255,
        Qgis.UInt16 : 65535,
        Qgis.UInt32 : 4294967295 }
    if type not in unsigned:
        utils.internal_error("Type " + str(type) + " is unsigned")
    return unsigned[type]
    
# Returns list of classic values to reprensent NoData pixels in raster layers
def getNDCandidates(type):
    if type in [ Qgis.Byte, Qgis.UInt16, Qgis.UInt32]:
        return [ 0,getQGISTypeMaxVal(type) ]
    else:
        return [ 0, -9999, -1 ]
        
# Returns a value to represent NoData pixels that does not already exist in vals
def getNDCandidate(type,vals):
    candidates = getNDCandidates(type)
    for cand in candidates:
        if cand not in vals:
            return cand
    utils.internal_error("Could not find a proper NoData value, exiting (please contact support)")
    
# Checks layers geometry compatibility (raise error if not compatible)
def checkLayersCompatible(l1,l2):
    crs1 = l1.crs().authid()
    crs2 = l2.crs().authid()
    if crs1 != crs2:
        utils.user_error("Layer " + l1.name() + " SRID '" + str(crs1)
                    + "' not compatible with SRID '" + str(crs2)
                    + "' of layer " + l2.name())
    geomType1 = l1.geometryType()
    geomType2 = l1.geometryType()
    if geomType1 != geomType2:
        utils.user_error("Layer " + l1.name() + " geometry '" + str(geomType1)
                    + "' not compatible with geometry '" + str(geomType2)
                    + "' of layer " + l2.name())
    
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
    
    
# Initialize new layer from existing one, importing CRS and geometry
def createLayerFromExisting(inLayer,outName,geomType=None,crs=None):
    utils.debug("[createLayerFromExisting]")
    # crs=str(inLayer.crs().authid()).lower()
    # geomType=QgsWkbTypes.displayString(inLayer.wkbType())
    if not crs:
        crs=getLayerCrsStr(inLayer)
    if not geomType:
        geomType=getLayerGeomStr(inLayer)
    layerStr = geomType + '?crs='+crs
    utils.debug(layerStr)
    outLayer=QgsVectorLayer(geomType + '?crs='+crs, outName, "memory")
    return outLayer
    
# Writes file from existing QgsMapLayer
def writeShapefile(layer,outfname):
    utils.debug("[writeShapefile] " + outfname + " from " + str(layer))
    if os.path.isfile(outfname):
        os.remove(outfname)
    (error, error_msg) = QgsVectorFileWriter.writeAsVectorFormat(layer,outfname,'utf-8',destCRS=layer.sourceCrs(),driverName='ESRI Shapefile')
    if error == QgsVectorFileWriter.NoError:
        utils.info("Shapefile '" + outfname + "' succesfully created")
    else:
        utils.user_error("Unable to create shapefile '" + outfname + "' : " + str(error_msg))
    
# Writes file from existing QgsMapLayer
def writeVectorLayer(layer,outfname,attributes=[]):
    utils.debug("[writeVectorLayer] " + outfname + " from " + str(layer))
    if os.path.isfile(outfname):
        os.remove(outfname)
    (error, error_msg) = QgsVectorFileWriter.writeAsVectorFormat(layer,outfname,
        'utf-8',destCRS=layer.sourceCrs(),attributes=attributes)
    if error == QgsVectorFileWriter.NoError:
        utils.info("File '" + outfname + "' succesfully created")
    else:
        utils.user_error("Unable to create file '" + outfname + "' : " + str(error_msg))
        
# Return bounding box coordinates as a list
def coordsOfExtentPath(extent_path):
    layer = loadLayer(extent_path)
    extent = layer.extent()
    x_min = extent.xMinimum()
    x_max = extent.xMaximum()
    y_min = extent.yMinimum()
    y_max = extent.yMaximum()
    return [str(x_min),str(y_min),str(x_max),str(y_max)]
    
def getExtentStrFromPath(extent_path,crs=None):
    extent_layer = loadLayer(extent_path)
    extent = extent_layer.extent()
    crs = extent_layer.crs()
    res = str(extent.xMinimum())
    res += ',' + str(extent.xMaximum())
    res += ',' + str(extent.yMinimum())
    res += ',' + str(extent.yMaximum())
    res += '[' + str(crs.authid()) + ']'
    return res
    
def transformBoundingBox(in_rect,in_crs,out_crs):
    transformator = QgsCoordinateTransform(in_crs,out_crs,QgsProject.instance())
    out_rect = transformator.transformBoundingBox(in_rect)
    return out_rect
    
def getLayerFieldUniqueValues(layer,fieldname):
    path = pathOfLayer(layer)
    fieldnames = layer.fields().names()
    if fieldname not in fieldnames:
        utils.internal_error("No field named '" + fieldname + "' in layer " + path)
    field_values = set()
    for f in layer.getFeatures():
        field_values.add(f[fieldname])
    return field_values
    
def getLayerAssocs(layer,key_field,val_field):
    assoc = {}
    path = pathOfLayer(layer)
    fieldnames = layer.fields().names()
    if key_field not in fieldnames:
        utils.internal_error("No field named '" + key_field + "' in layer " + path)
    if val_field not in fieldnames:
        utils.internal_error("No field named '" + val_field + "' in layer " + path)
    for f in layer.getFeatures():
        k = f[key_field]
        v = f[val_field]
        if k in assoc:
            old_v = assoc[k]
            if v not in old_v:
                old_v.append(v)
        else:
            assoc[k] = [v]
    return assoc
   
""" Raster utilities """
   
# Code snippet from https://github.com/Martin-Jung/LecoS/blob/master/lecos_functions.py
# Exports array to .tif file (path) according to rasterSource
def exportRaster(array,rasterSource,path,
                 nodata=None,type=None,copt=GTIFF_COPT):
    raster = gdal.Open(str(rasterSource))
    rows = raster.RasterYSize
    cols = raster.RasterXSize
    raster_band1 = raster.GetRasterBand(1)
    out_type = raster_band1.DataType
    out_nodata = raster_band1.GetNoDataValue()
    if nodata is not None:
        out_nodata = nodata
    if type:
        out_type = type
    if copt is None:
        copt = []
    elif not isinstance(copt, list):
        utils.internal_error("Could not apply GDAL creation options : " + str(copt))

    driver = gdal.GetDriverByName('GTiff')
    # Create File based in path
    try:
        outDs = driver.Create(path, cols, rows, 1, out_type, copt)
    except RuntimeError:
        utils.internal_error("Could not overwrite file. Check permissions!")
    if outDs is None:
        utils.internal_error("Could not create output File. Check permissions!")

    band = outDs.GetRasterBand(1)
    band.WriteArray(array)

    # flush data to disk, set the NoData value
    band.FlushCache()
    try:
        band.SetNoDataValue(out_nodata)
    except TypeError:
        band.SetNoDataValue(-9999) # set -9999 in the meantime

    # georeference the image and set the projection
    outDs.SetGeoTransform(raster.GetGeoTransform())
    outDs.SetProjection(raster.GetProjection())

    band = outDs = None # Close writing
    
def getRasterValsFromPath(path):
    gdal_layer = gdal.Open(path)
    if not gdal_layer:
        utils.user_error("Could not load raster " + str(path))
    band1 = gdal_layer.GetRasterBand(1)
    data_array = band1.ReadAsArray()
    unique_vals = set(np.unique(data_array))
    utils.debug("Unique values init : " + str(unique_vals))
    in_nodata_val = band1.GetNoDataValue()
    utils.debug("in_nodata_val = " + str(in_nodata_val))
    if in_nodata_val in unique_vals:
        unique_vals.remove(in_nodata_val)
    utils.debug("Unique values : " + str(unique_vals))
    return unique_vals
    
# IMPORT GDAL OR NOT ?
def getRasterValsOld(layer):
    path = pathOfLayer(layer)
    gdal_layer = gdal.Open(path)
    band1 = gdal_layer.GetRasterBand(1)
    data_array = band1.ReadAsArray()
    unique_vals = set(np.unique(data_array))
    utils.debug("Unique values init : " + str(unique_vals))
    in_nodata_val = int(band1.GetNoDataValue())
    utils.debug("in_nodata_val = " + str(in_nodata_val))
    unique_vals.remove(in_nodata_val)
    utils.debug("Unique values : " + str(unique_vals))
    return unique_vals
    
def getRasterValsBis(layer):
    if layer is None:
        return []
    rows = layer.height()
    cols = layer.width()
    dpr = layer.dataProvider()
    bl = dpr.block(1, dpr.extent(), cols, rows) # 1: band no
    nodata_val = dpr.sourceNoDataValue(1)
    unique_values = set([bl.value(r, c) for r in range(rows) for c in range(cols)])
    unique_values.remove(nodata_val)
    return list(unique_values)
    
def getRasterValsAndArray(path,nodata=None):
    raster = gdal.Open(str(path))
    if not raster:
        utils.user_error("Could not open raster path '" + str(path) + "'")
    if(raster.RasterCount==1):
        band = raster.GetRasterBand(1)
        if nodata == None:
            nodata = band.GetNoDataValue()
        try:
            array =  band.ReadAsArray() 
        except ValueError:
            utils.internal_error("Raster file is too big for processing. Please crop the file and try again.")
            return
        classes = sorted(np.unique(array)) # get classes
        try:
            classes.remove(nodata)
        except ValueError:
            pass
        return classes, array
    else:
        utils.user_error("Multiband Rasters not implemented yet")
def getRasterValsArrayND(path,nodata=None):
    raster = gdal.Open(str(path))
    if not raster:
        utils.user_error("Could not open raster path '" + str(path) + "'")
    if(raster.RasterCount==1):
        band = raster.GetRasterBand(1)
        if nodata == None:
            nodata = band.GetNoDataValue()
        try:
            array =  band.ReadAsArray() 
        except ValueError:
            utils.internal_error("Raster file is too big for processing. Please crop the file and try again.")
            return
        classes = sorted(np.unique(array)) # get classes
        try:
            classes.remove(nodata)
        except ValueError:
            pass
        return classes, array, nodata
    else:
        utils.user_error("Multiband Rasters not implemented yet")
# def getHistogram(layer):
    # pr = layer.dataProvider()
    # hist = pr.histogram(1)
    # if not pr.hasHistogram(1,0):
        # utils.debug("init")
        # pr.initHistogram(hist,1,0)
    # utils.debug("hist = " + str(hist))
    # return hist
       
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
    
# def getRasterNoData(layer):
    # band1 = layer.GetRasterBand(1)
    # nodata_val = band1.GetNoDataValue()
    # return nodata_val
    
# def getRasterResolution(layer):
    # pass
    
def getVectorValsOld(layer,field_name):
    field_values = set()
    for f in layer.getFeatures():
        field_values.add(f[field_name])
    return sorted(field_values)
    
def getVectorVals(layer,field_name):
    idx = layer.dataProvider().fieldNameIndex(field_name)
    return layer.uniqueValues(idx)


def checkProjectionUnit(layer):
    if layer is not None:
        if layer.crs().mapUnits() != 0: # QgsUnitTypes.encodeUnit(0) == "meters"
            utils.internal_error("The layer "+layer.name()+" has a projection in "+layer.crs().authid()+", with "+QgsUnitTypes.encodeUnit(layer.crs().mapUnits())+" unit, it must be in meter unit (like EPSG:2154).")


""" GPKG """ 

# Geopackages 'fid'
def getMaxFid(layer):
    max = 1
    for f in layer.getFeatures():
        id = f["fid"]
        id = f.id()
        if id > max:
            max = id
    return max
    
def normFids(layer):
    max_fid = 1
    feats = layer.getFeatures()
    layer.startEditing()
    for f in feats:
        layer.changeAttributeValue(f.id(),0,max_fid)
        #f.setId(max_fid)
        max_fid += 1
    layer.commitChanges()


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
        
# Layer ComboDialog
class LayerComboDialog:

    def __init__(self,parent,combo,button):
        self.parent = parent
        self.combo = combo
        self.button = button
        self.layer_name = None
        self.layer = None
        self.vector_mode = None
        self.button.clicked.connect(self.openDialog)
        
    def setVectorMode(self):
        self.vector_mode = True
        self.combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        
    def setRasterMode(self):
        self.vector_mode = False
        self.combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        
    def setBothMode(self):
        self.vector_mode = None
        self.combo.setFilters(QgsMapLayerProxyModel.All)
        
    def setLayerPath(self,fname):
        self.combo.setLayer(None)
        self.layer_name = fname
        if self.vector_mode is None:
            self.layer = loadLayer(fname,loadProject=True)
        elif self.vector_mode:
            self.layer = loadVectorLayer(fname,loadProject=True)
        else:
            self.layer = loadRasterLayer(fname,loadProject=True)
        # utils.debug("self.layer = " +str(self.layer))
        self.combo.setLayer(self.layer)
        
        
    def getFileFilters(self):
        if self.vector_mode:
            return getVectorFilters()
        else:
            return getRasterFilters()
        
    def openDialog(self):
        fname = openFileDialog(self.parent,
                                     msg="Ouvrir la couche",
                                     filter=self.getFileFilters())
        if fname:
            self.setLayerPath(fname)
            #self.combo.layerChanged.emit(self.layer)
        # else:
            # self.parent.feedback.user_error("Could not open file " + str(fname))
        
    def getLayer(self):
        return self.layer


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
    def setAndCheckOutputCSV(self,parameters):
        self.output = self.parameterAsString(parameters,self.OUTPUT,self.context)
        self.feedback.pushDebugInfo("output = {}".format(self.output))
        if not self.output or self.output.endswith(".file"):
            self.output = mkTmpPath('output.csv')
            self.feedback.pushDebugInfo("output = {}".format(self.output))
        if utils.fileExists(self.output):
            utils.removeFile(self.output)

# Plugin utils

def checkPluginInstalled(pluginName):
    pluginList = QgsProviderRegistry.instance().pluginList()
    utils.debug("pluginList = " + str(pluginList))
    return (pluginName in pluginList)
    
def getPluginInstance(pluginName,errorOK=False):
    if pluginName not in qgis.utils.plugins:
        if errorOK:
            return None
        else:
            raise QgsProcessingException("Plugin {} not installed".format(pluginName))
    pluginInstance = qgis.utils.plugins[pluginName]
    return pluginInstance
    
def mkProcTmpPath(fname):
    return QgsProcessingUtils.generateTempFilename(fname)

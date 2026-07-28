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
    Proxy functions to call usual processing algorithms.
"""

from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsProcessingUtils,
    QgsFeatureRequest,
    QgsProcessingContext,
    QgsRasterLayer
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QGuiApplication

import os.path
import time

import processing

from . import utils, qgsUtils

nodata_val = '-9999'
MEMORY_LAYER_NAME = 'memory:'
# GTIFF_COPT = qgsUtils.GTIFF_COPT
gtiff_copt_flag = False
GTIFF_COPT = qgsUtils.GTIFF_COPT if gtiff_copt_flag else []
gtiff_opts_pipe = '|'.join(GTIFF_COPT)
# gtiff_opts_comma = ','.join(GTIFF_COPT)

# Processing call wrappers

def applyProcessingAlg(provider,alg_name,parameters,context=None,
        feedback=None,onlyOutput=True):
    # Dummy function to enable running an alg inside an alg
    def no_post_process(alg, context, feedback):
        pass
    if feedback is None:
        utils.internal_error("No feedback")
    feedback.pushDebugInfo("parameters : " + str(parameters))
    QGuiApplication.processEvents()
    try:
        complete_name = provider + ":" + alg_name
        feedback.pushInfo("Calling processing algorithm '" + complete_name + "'")
        start_time = time.time()
        context = None
        #utils.debug("context = " + str(context))
        if context is None:
            context = QgsProcessingContext()
            context.setFeedback(feedback)
        feedback.pushDebugInfo("complete_name = " + str(complete_name))
        feedback.pushDebugInfo("feedback = " + str(feedback.__class__.__name__))
        # assert(False)
        res = processing.run(complete_name,parameters,onFinish=no_post_process,context=context,feedback=feedback)
        #res = processing.runAndLoadResults(complete_name,parameters,context=context,feedback=feedback)#,onFinish=no_post_process)
        feedback.pushDebugInfo("res1 = " + str(res))
        end_time = time.time()
        diff_time = end_time - start_time
        feedback.pushInfo("Call to " + alg_name + " successful"
                    + ", performed in " + str(diff_time) + " seconds")
        # feedback.endJob()
        feedback.pushDebugInfo("res = " + str(res))
        if onlyOutput:
            if "OUTPUT" in res:
                feedback.pushDebugInfo("output = " + str(res["OUTPUT"]))
                feedback.pushDebugInfo("output type = " + str(type(res["OUTPUT"])))
                return res["OUTPUT"]
            elif 'output' in res:
                return res['output']
            else:
                return None
        else:
            return res
    except Exception as e:
        feedback.pushWarning ("Failed to call " + alg_name + " : " + str(e))
        raise e
    finally:
        feedback.pushDebugInfo("End run " + alg_name)

# class ProcessingAlgTask(QgsTask):

    # def __init__(self,provider,algName,parameters,context=None,feedback=None,onlyOutput=None):
        # self.provider = provider
        # self.algName = algName
        # self.parameters = parameters
        # self.context = context
        # self.feedback = feedback
        # self.onlyOutput = onlyOutput

    # def run(self):
        # return applyProcessingAlgFunc(self.provider,algName,parameters,
            # context=context,feedback=feedback,onlyOutput=onlyOutput)

# def applyProcessingAlg(provider,algName,parameters,context=None,
        # feedback=None,onlyOutput=True,background=True):
    # task = ProcessingAlgTask(provider,algName,parameters,context=context,
        # feedback=feedback,onlyOutput=onlyOutput)


def checkGrass7Installed():
    try:
        versionInt = Qgis.versionInt()
        if versionInt >= 3.22:
            return
        else:
            grass7 = processing.algs.grass7.Grass7Utils.Grass7Utils
            if grass7:
                grass7.checkGrassIsInstalled()
                if grass7.isGrassInstalled:
                    return
                version = grass7.version
                if version:
                    utils.debug("GRASS version1 = " + str(version))
                    utils.debug("GRASS version1 type = " + str(type(version)))
                    return
                version = grass7.installedVersion()
                if version:
                    utils.debug("GRASS version3 = " + str(version))
                    utils.debug("GRASS version3 type = " + str(type(version)))
                    return
                utils.user_error("GRASS version not found, please launch QGIS with GRASS")
            else:
                utils.user_error("GRASS module not found, please launch QGIS with GRASS")
    except AttributeError:
        utils.warn("Could not detect GRASS, please ensure QGIS is launched with GRASS")

def applyGrassAlg(alg_name,parameters,context,feedback):
    checkGrass7Installed()
    return applyProcessingAlg("grass7",alg_name,parameters,context,feedback)

# Types normalization

USE_INPUT_TYPE = -1

# QGIS type converted to integer to be passed as a processing alg parameter
# Parameter shift return integer value according to TYPES list
# If input qgis_type is unknown, it is cast to defaultType
# If input value is -1, it means 'Use input layer data type' and return value is 0
def qgsTypeToInt(qgis_type,shift=False,typeList=2):
    if isinstance(qgis_type,Qgis.DataType):
        TYPES1 = [Qgis.DataType.Byte, Qgis.DataType.Int16, Qgis.DataType.UInt16, Qgis.DataType.Int32, Qgis.DataType.UInt32, Qgis.DataType.Float32,
                 Qgis.DataType.Float64, Qgis.DataType.CInt16, Qgis.DataType.CInt32, Qgis.DataType.CFloat32, Qgis.DataType.CFloat64]
        TYPES2 = [Qgis.DataType.Byte, Qgis.DataType.Int16, Qgis.DataType.UInt16, Qgis.DataType.UInt32, Qgis.DataType.Int32, Qgis.DataType.Float32,
                 Qgis.DataType.Float64, Qgis.DataType.CInt16, Qgis.DataType.CInt32, Qgis.DataType.CFloat32, Qgis.DataType.CFloat64]
        TYPES3 = [Qgis.DataType.Byte, Qgis.DataType.UInt16, Qgis.DataType.Int16, Qgis.DataType.UInt32, Qgis.DataType.Int32, Qgis.DataType.Float32,
                 Qgis.DataType.Float64, Qgis.DataType.CInt16, Qgis.DataType.CInt32, Qgis.DataType.CFloat32, Qgis.DataType.CFloat64]
        if typeList == 1:
            typeList = TYPES1
        elif typeList == 2:
            typeList = TYPES2
        elif typeList == 3:
            typeList = TYPES3
        else:
            utils.internal_error("No type list with id " + str(typeList))
        if qgis_type in typeList:
            int_value = typeList.index(qgis_type)
            if not shift:
                int_value += 1
            utils.debug("qgsTypeToInt " + str(qgis_type) + " = " + str(int_value))
            return int_value
        else:
            utils.internal_error("No type associated to qgis type " + str(qgis_type))
    elif isinstance(qgis_type,int):
        int_value = 0 if qgis_type == USE_INPUT_TYPE else qgis_type
        return int_value
    else:
        utils.internal_error("No integer value associated to qgis type " + str(qgis_type))


# Processing utils

def parameterAsSourceLayer(obj_alg,parameters,paramName,context,feedback=None):
    source = obj_alg.parameterAsSource(parameters,paramName,context)
    if source:
        layer = source.materialize(QgsFeatureRequest(),feedback=feedback)
    else:
        layer = None
    return source, layer

# Vector algorithms

def joinByLoc(layer1,layer2,predicates=[0],out_path=MEMORY_LAYER_NAME,
        discard=True,fields=[],method=0,prefix='',non_matching=None,
        context=None,feedback=None):
    parameters = { 'DISCARD_NONMATCHING' : discard,
        'INPUT' : layer1,
        'JOIN' : layer2,
        'JOIN_FIELDS' : fields,
        'METHOD' : method,
        'OUTPUT' : out_path,
        'PREDICATE' : predicates,
        'PREFIX' : prefix }
    if not discard and non_matching:
        parameters['NON_MATCHING'] = non_matching
    res = applyProcessingAlg("qgis","joinattributesbylocation",parameters,context=context,feedback=feedback)
    return res

def joinByLocSummary(in_layer,join_layer,out_layer,fieldnames=[],summaries=[],
        predicates=[0],discard=True,non_matching=None,
        context=None,feedback=None):
    parameters = { 'DISCARD_NONMATCHING' : discard,
        'INPUT' : in_layer,
        'JOIN' : join_layer,
        'JOIN_FIELDS' : fieldnames,
        'OUTPUT' : out_layer,
        'PREDICATE' : predicates,
        'SUMMARIES' : summaries }
    if not discard and non_matching:
        parameters['NON_MATCHING'] = non_matching
    res = applyProcessingAlg("qgis","joinbylocationsummary",
        parameters,context=context,feedback=feedback)
    return res

def joinByAttribute(layer1,field1,layer2,field2,out_layer,
        copy_fields=None,method=1,discard=False,prefix='',
        context=None,feedback=None):
    parameters = { 'DISCARD_NONMATCHING' : True,
        'FIELD' : field1,
        'FIELDS_TO_COPY' : copy_fields,
        'FIELD_2' : field2,
        'INPUT' : layer1,
        'INPUT_2' : layer2,
        'METHOD' : method,
        'DISCARD_NONMATCHING' : discard,
        'OUTPUT' : out_layer,
        'PREFIX' : prefix }
    res = applyProcessingAlg("qgis","joinattributestable",
        parameters,context=context,feedback=feedback)
    return res

def extractByExpression(in_layer,expr,out_layer,fail_out=None,context=None,feedback=None):
    parameters = { 'EXPRESSION' : expr,
                   'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    if fail_out:
        parameters['FAIL_OUTPUT'] = fail_out
    res = applyProcessingAlg("native","extractbyexpression",parameters,context=context,feedback=feedback)
    return res

# predicate = 0 <=> intersection
def extractByLoc(in_layer,loc_layer,out_layer,predicate=[0],context=None,feedback=None):
    parameters = { 'PREDICATE' : predicate,
                   'INTERSECT' : loc_layer,
                   'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    res = applyProcessingAlg("native","extractbylocation",parameters,context=context,feedback=feedback)
    return res

def saveSelectedAttributes(in_layer,out_layer,context=None,feedback=None):
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    res = applyProcessingAlg("native","saveselectedfeatures",parameters,context=context,feedback=feedback)
    return res

def multiToSingleGeom(in_layer,out_layer,context=None,feedback=None):
    feedback.setProgressText("Multi to single geometry")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    res = applyProcessingAlg("native","multiparttosingleparts",parameters,context=context,feedback=feedback)
    return res

def dissolveLayer(in_layer,out_layer,fields=[],context=None,feedback=None):
    #utils.checkFileExists(in_layer)
    feedback.setProgressText("Dissolve")
    #feedback.setProgressText("Dissolve " + str(in_layer))
    #if out_layer:
    #    qgsUtils.removeVectorLayer(out_layer)
    parameters = { 'FIELD' : fields,
                   'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    if feedback:
        feedback.pushInfo("parameters = " + str(parameters))
    res = applyProcessingAlg("native","dissolve",parameters,context,feedback)
    return res

def applyBufferFromExpr(in_layer,expr,out_layer,context=None,feedback=None,cap_style=0):
    #utils.checkFileExists(in_layer)
    feedback.setProgressText("Buffering")
    #feedback.setProgressText("Buffer (" + str(expr) + ") on " + str(out_layer))
    #if out_layer:
    #    qgsUtils.removeVectorLayer(out_layer)
    parameters = { 'DISSOLVE' : False,
                   #'DISTANCE' : QgsProperty.fromExpression(expr),
                   'DISTANCE' : expr,
                   'INPUT' : in_layer,
                   'OUTPUT' : out_layer,
                   'END_CAP_STYLE' : cap_style,
                   'JOIN_STYLE' : 0,
                   'MITER_LIMIT' : 2,
                   'SEGMENTS' : 5 }
    res = applyProcessingAlg("native","buffer",parameters,context,feedback)
    return res


def mergeVectorLayers(in_layers,crs,out_layer,context=None,feedback=None):
    feedback.setProgressText("Merge vector layers")
    parameters = { 'CRS' : crs,
                   'LAYERS' : in_layers,
                   'OUTPUT' : out_layer }
    res = applyProcessingAlg("native","mergevectorlayers",parameters,context,feedback)
    return res


def applyDifference(in_layer,diff_layer,out_layer,context=None,feedback=None):
    feedback.setProgressText("Difference")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer,
                   'OVERLAY' : diff_layer }
    res = applyProcessingAlg("native","difference",parameters,context=context,feedback=feedback)
    return res

def applyVectorClip(in_layer,clip_layer,out_layer,context=None,feedback=None):
    feedback.setProgressText("Clip")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer,
                   'OVERLAY' : clip_layer }
    res = applyProcessingAlg("qgis","clip",parameters,context,feedback)
    return res

def applyReprojectLayer(in_layer,target_crs,out_layer,context=None,feedback=None):
    feedback.setProgressText("Reproject")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer,
                   'TARGET_CRS' : target_crs }
    res = applyProcessingAlg("native","reprojectlayer",parameters,context,feedback)
    return res

def createGridLayer(extent,crs,size,out_layer, gtype=2, context=None,feedback=None):
    parameters = {
        'CRS' : crs,
        'EXTENT' : extent,
        'HOVERLAY' : 0,
        'HSPACING' : size,
        'VOVERLAY' : 0,
        'VSPACING' : size,
        'OUTPUT' : out_layer,
        'TYPE' : gtype } #2 - Rectangle
    res = applyProcessingAlg("native","creategrid",parameters,context,feedback)
    return res

def fixGeometries(input,output,context=None,feedback=None):
    parameters = {'INPUT' : input, 'OUTPUT' : output }
    res = applyProcessingAlg("native","fixgeometries",parameters,context,feedback)
    return res

def assignProjection(input,crs,output,context=None,feedback=None):
    parameters = { 'CRS' : crs, 'INPUT' : input, 'OUTPUT' : output }
    res = applyProcessingAlg("native","assignprojection",parameters,context,feedback)
    return res

# Careful with minimal version (3.16 ?)
def createSpatialIndex(input,context=None,feedback=None):
    parameters = { 'INPUT' : input}
    try:
        return applyProcessingAlg("native","createspatialindex",parameters,context,feedback)
    except Exception as e:
        feedback.reportError(str(e))

def applyVoronoi(input,output,buffer=0,context=None,feedback=None):
    parameters = { 'INPUT' : input, 'BUFFER' : buffer, 'OUTPUT' : output }
    return applyProcessingAlg("qgis","voronoipolygons",parameters,context,feedback)

def fixShapefileFID(input,context=None,feedback=None):
    feedback.pushDebugInfo("input = " + str(input))
    feedback.pushDebugInfo("input type = " + str(type(input)))
    if type(input) is str:
        input_path = input
        input_layer = qgsUtils.loadVectorLayer(input)
    else:
        input_path = qgsUtils.pathOfLayer(input)
        input_layer = input
    extension = os.path.splitext(input_path)[1].lower()
    if extension != '.shp':
        return input
    fid_idx = input_layer.fields().indexFromName('fid')
    if fid_idx == -1:
        return input
    else:
        input_layer.startEditing()
        input_layer.deleteAttribute(fid_idx)
        input_layer.commitChanges()
        return input


"""
    QGIS RASTER ALGORITHMS
"""

def rasterZonalStats(vector,raster,output,prefix='_',band=1,stats=[0,1,2],context=None,feedback=None):
    parameters = { 'COLUMN_PREFIX' : prefix,
        'INPUT' : vector,
        'INPUT_RASTER' : raster,
        'OUTPUT' : output,
        'RASTER_BAND' : band,
        'STATISTICS' : stats }
    return applyProcessingAlg("native","zonalstatisticsfb",parameters,context,feedback)

def applyHeatmap(input, output, resolution=5, radius_field=None,
        weight_field=None, context=None, feedback=None):
    parameters = {
        'DECAY' : 0,
        'INPUT' : input,
        'KERNEL' : 0,
        'OUTPUT' : output,
        'OUTPUT_VALUE' : 0,
        'PIXEL_SIZE' : resolution,
        'RADIUS' : None,
        'RADIUS_FIELD' : radius_field,
        'WEIGHT_FIELD' : weight_field }
    res = applyProcessingAlg("qgis","heatmapkerneldensityestimation",parameters,context,feedback)
    return res

"""
    GDAL RASTER ALGORITHMS
"""

# Apply rasterization on field 'field' of vector layer 'in_path'.
# Output raster layer in 'out_path'.
# Resolution set to 25 if not given.
# Extent can be given through 'extent_path'. If not, it is extracted from input layer.
# Output raster layer is loaded in QGIS if 'load_flag' is True.
def applyRasterization(in_path,out_path,extent,resolution,
                       field=None,burn_val=None,out_type=Qgis.DataType.Float32,
                       nodata_val=nodata_val,all_touch=False,overwrite=False,
                       context=None,feedback=None,options=gtiff_opts_pipe):
    TYPES = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32',
             'Float64', Qgis.DataType.CInt16, Qgis.DataType.CInt32, 'CFloat32', 'CFloat64']
    #utils.debug("applyRasterization")
    feedback.setProgressText("Rasterize")
    if overwrite:
        qgsUtils.removeRaster(out_path)
    parameters = { 'ALL_TOUCH' : all_touch,
                   'BURN' : burn_val,
                   'DATA_TYPE' : qgsTypeToInt(out_type,shift=True),
                   'EXTENT' : extent,
                   'FIELD' : field,
                   'HEIGHT' : resolution,
                   #'INIT' : None,
                   'INPUT' : in_path,
                   #'INVERT' : False,
                   'NODATA' : nodata_val,
                   'OPTIONS' : options,
                   'OUTPUT' : out_path,
                   'UNITS' : 1,
                   'WIDTH' : resolution }
    extra_param_name = 'EXTRA'
    if all_touch:
        if hasattr(processing.algs.gdal.rasterize.rasterize,extra_param_name):
            parameters['EXTRA'] = '-at'
        else:
            parameters['ALL_TOUCH'] = True
    res = applyProcessingAlg("gdal","rasterize",parameters,context,feedback)
    return res

def applyRasterizeOver(input_layer, input_raster, field, add=True, context=None,feedback=None):
    parameters = {
        'ADD': add,
        'EXTRA': '',
        'FIELD': field,
        'INPUT': input_layer,
        'INPUT_RASTER': input_raster
    }
    return applyProcessingAlg("gdal","rasterize_over", parameters,context,feedback)

def applyWarpReproject(in_path,out_path,resampling_mode='near',dst_crs=None,
                       src_crs=None,extent=None,extent_crs=None,
                       resolution=None,out_type=USE_INPUT_TYPE,nodata_val=nodata_val,
                       overwrite=False,context=None,feedback=None):
    feedback.setProgressText("Warp")
    modes = ['near', 'bilinear', 'cubic', 'cubicspline', 'lanczos',
             'average','mode', 'max', 'min', 'med', 'q1', 'q3']
    # Resampling mode
    if resampling_mode not in modes:
        utils.internal_error("Unexpected resampling mode : " + str(resampling_mode))
    mode_val = modes.index(resampling_mode)
    if overwrite:
        qgsUtils.removeRaster(out_path)
    # Output type
    TYPES = ['Use input layer data type', 'Byte', 'Int16', 'UInt16', 'UInt32', 'Int32',
             'Float32', 'Float64', Qgis.DataType.CInt16, Qgis.DataType.CInt32, 'CFloat32', 'CFloat64']
    # Parameters
    parameters = { 'DATA_TYPE' : qgsTypeToInt(out_type),
                   'INPUT' : in_path,
                   'NODATA' : nodata_val,
                   'OUTPUT' : out_path,
                   'OPTIONS' : gtiff_opts_pipe,
                   'RESAMPLING' : mode_val,
                   'SOURCE_CRS' : src_crs,
                   'TARGET_CRS' : dst_crs,
                   'TARGET_EXTENT' : extent,
                   'TARGET_EXTENT_CRS' : extent_crs,
                   'TARGET_RESOLUTION' : resolution }
    return applyProcessingAlg("gdal","warpreproject",parameters,context,feedback)

def applyTranslate(in_path,out_path,data_type=USE_INPUT_TYPE,nodata_val=nodata_val,
                   crs=None,options=gtiff_opts_pipe,context=None,feedback=None):
    feedback.setProgressText("Tanslate")
    # data type 0 = input raster type
    parameters = { 'COPY_SUBDATASETS' : False,
                   'DATA_TYPE' : qgsTypeToInt(data_type),
                   'INPUT' : in_path,
                   'NODATA' : nodata_val,
                   'OUTPUT' : out_path,
                   'OPTIONS' : options,
                   'TARGET_CRS' : None }
    return applyProcessingAlg("gdal","translate",parameters,context,feedback)


def clipRasterFromVector(raster_path,vector_path,out_path,
                         resolution=None,x_res=None,y_res=None,keep_res=True,
                         crop_cutline=True,nodata=None,data_type=USE_INPUT_TYPE,
                         context=None,feedback=None):
    # data type 0 = input raster type
    feedback.setProgressText("Clip raster")
    parameters = { 'ALPHA_BAND' : False,
                   'CROP_TO_CUTLINE' : crop_cutline,
                   'DATA_TYPE' : qgsTypeToInt(data_type),
                   'INPUT' : raster_path,
                   'KEEP_RESOLUTION' : keep_res,
                   'MASK' : vector_path,
                   'NODATA' : nodata,
                   'OPTIONS' : gtiff_opts_pipe,
                   'OUTPUT' : out_path }
    if resolution:
        parameters['KEEP_RESOLUTION'] = False
        parameters['SET_RESOLUTION'] = True
        parameters['X_RESOLUTION'] = resolution
        parameters['Y_RESOLUTION'] = resolution
    if x_res and y_res:
        parameters['KEEP_RESOLUTION'] = False
        parameters['SET_RESOLUTION'] = True
        parameters['X_RESOLUTION'] = x_res
        parameters['Y_RESOLUTION'] = y_res
    # parameters = {'ALPHA_BAND': False, 'CROP_TO_CUTLINE': True, 'DATA_TYPE': 0, 'INPUT': 'D:/IRSTEA/BioDispersal/Tests/BousquetOrbExtended/Groups/landuse/landuse_raster.tif', 'KEEP_RESOLUTION': True, 'MASK': 'D:\\IRSTEA\\BioDispersal\\Tests\\BousquetOrbExtended\\Source\\ZoneEtude\\EPCIBousquetOrbBuf4000.shp', 'NODATA': None, 'OUTPUT': 'D:/IRSTEA/BioDispersal/Tests/BousquetOrbExtended/Groups/landuse/landuse.tif', 'SET_RESOLUTION': True, 'X_RESOLUTION': 25.0, 'Y_RESOLUTION': 25.0}
    # parameters = { 'ALPHA_BAND' : False, 'CROP_TO_CUTLINE' : True, 'DATA_TYPE' : 0, 'EXTRA' : '', 'INPUT' : 'D:/IRSTEA/ERC/tests/BousquetOrbExtended/Source/CorineLandCover/CLC12_BOUSQUET_ORB.tif', 'KEEP_RESOLUTION' : False, 'MASK' : 'D:/IRSTEA/ERC/tests/BousquetOrbExtended/Source/ZoneEtude/EPCIBousquetOrb.shp', 'MULTITHREADING' : False, 'NODATA' : None, 'OPTIONS' : '', 'OUTPUT' : out_path, 'SET_RESOLUTION' : False, 'SOURCE_CRS' : None, 'TARGET_CRS' : None, 'X_RESOLUTION' : 10, 'Y_RESOLUTION' : 10 }
    return applyProcessingAlg("gdal","cliprasterbymasklayer",parameters,
        context=context,feedback=feedback)

def applyMergeRaster(files,output,nodata_val=nodata_val,out_type=Qgis.DataType.Float32,
                     nodata_input=None,pct=False,separate=False,options=gtiff_opts_pipe,
                     context=None,feedback=None):
    TYPES = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64',
        'CInt16', 'CInt32', 'CFloat32', 'CFloat64']
    feedback.setProgressText("Merge raster")
    parameters = {
            'DATA_TYPE': qgsTypeToInt(out_type,shift=True),
            'EXTRA': '',
            'INPUT': files,
            'NODATA_INPUT': nodata_input,
            'NODATA_OUTPUT': nodata_val,
            'OPTIONS' : options,
            'PCT': pct,
            'SEPARATE': separate,
            'OUTPUT': output
        }
    return applyProcessingAlg("gdal","merge",parameters,context,feedback)

def applyRasterCalcProc(input_a,output,expr,
                    nodata_val=nodata_val,out_type=Qgis.DataType.Float32,
                    context=None,feedback=None):
    TYPE = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64']
    feedback.setProgressText("Raster Calc")
    parameters = { 'BAND_A' : 1,
                   'FORMULA' : expr,
                   'INPUT_A' : input_a,
                   'NO_DATA' : nodata_val,
                   'OUTPUT' : output,
                   'OPTIONS' : gtiff_opts_pipe,
                   'RTYPE' : qgsTypeToInt(out_type,shift=True) }
    return applyProcessingAlg("gdal","rastercalculator",parameters,context,feedback)

# Temporary workaround to fix UnicodeDecodeError
def applyRasterCalc(input_a,output,expr,
                    nodata_val=nodata_val,out_type=Qgis.DataType.Float32,
                    context=None,feedback=None):
    out_type = qgsTypeToInt(out_type,shift=True)
    if isinstance(input_a,QgsRasterLayer):
        input_a = qgsUtils.pathOfLayer(input_a)
    # TYPE = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64']
    # type_str = TYPE[out_type]
    #applyGdalCalc(input_a,output,expr,type=type_str,nodata=nodata_val)
    applyRasterCalcProc(input_a,output,expr,nodata_val=nodata_val,
        out_type=out_type,context=context,feedback=feedback)
    return output

def applyRasterCalcAB(input_a,input_b,output,expr,
                    nodata_val=nodata_val,out_type=Qgis.DataType.Float32,
                    context=None,feedback=None):
    TYPE = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64']
    parameters = { 'BAND_A' : 1,
                   'BAND_B' : 1,
                   'FORMULA' : expr,
                   'INPUT_A' : input_a,
                   'INPUT_B' : input_b,
                   'NO_DATA' : nodata_val,
                   'OUTPUT' : output,
                   'OPTIONS' : gtiff_opts_pipe,
                   'RTYPE' : qgsTypeToInt(out_type,shift=True) }
    return applyProcessingAlg("gdal","rastercalculator",parameters,
               context=context,feedback=feedback)

def applyRasterCalcABC(input_a,input_b,input_c, band_a, band_b, band_c, output,expr,
                    nodata_val=None,out_type=Qgis.DataType.Float32,
                    context=None,feedback=None):
    TYPE = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64']
    parameters = { 'BAND_A' : band_a,
                   'BAND_B' : band_b,
                   'BAND_C' : band_c,
                   'FORMULA' : expr,
                   'INPUT_A' : input_a,
                   'INPUT_B' : input_b,
                   'INPUT_C' : input_c,
                   'NO_DATA' : nodata_val,
                   'OPTIONS' : gtiff_opts_pipe,
                   'OUTPUT' : output,
                   'RTYPE' : qgsTypeToInt(out_type,shift=True) }
    return applyProcessingAlg("gdal","rastercalculator",parameters,context,feedback)

def applyBuildVirtualRaster(list_raster, output, crs=None, context=None,feedback=None):
    parameters = {
        'INPUT': list_raster,
        'RESOLUTION':0,
        'SEPARATE':False,
        'PROJ_DIFFERENCE':False,
        'ADD_ALPHA':False,
        'ASSIGN_CRS':crs,
        'RESAMPLING':0,
        'SRC_NODATA':'',
        'EXTRA':'',
        'OUTPUT': output
    }
    return applyProcessingAlg("gdal","buildvirtualraster",parameters,context,feedback)

"""
    TO CLASSIFY
"""

def getMajorityValue(inputVector, inputRaster, band, field_stat, context, feedback):
    zonal_stats = QgsProcessingUtils.generateTempFilename('zonal_stats_band_'+str(band)+'.gpkg')
    rasterZonalStats(inputVector, inputRaster,zonal_stats,prefix="_",band=band,stats=[9],context=context,feedback=feedback)
    stats_layer = qgsUtils.loadVectorLayer(zonal_stats)
    stats_fields = stats_layer.fields()
    stats_fieldnames = stats_fields.names()
    majority = 1 # default value
    if field_stat in stats_fieldnames:
        for f in stats_layer.getFeatures():
            majority = f[field_stat]
            break
    return majority

def applyGetLayerExtent(input_raster, output, context=None,feedback=None):
    parameters = {
        'INPUT': input_raster,
        'ROUND_TO': 0,
        'OUTPUT': output
    }
    return applyProcessingAlg("native","polygonfromlayerextent", parameters,context,feedback)

def applyClipRasterByExtent(input_raster, input_extent, output, data_type=0, options=gtiff_opts_pipe, no_data=None, context=None,feedback=None):
    parameters = {
        'DATA_TYPE': data_type,  # Utiliser le type de donnée de la couche en entrée
        'EXTRA': '',
        'INPUT': input_raster,
        'NODATA': no_data,
        'OPTIONS' : options,
        'OVERCRS': False,
        'PROJWIN': input_extent,
        'OUTPUT': output
    }
    return applyProcessingAlg("gdal","cliprasterbyextent", parameters,context,feedback)

def applyPolygonize(input_layer, field, output, band=1, context=None,feedback=None):
    parameters = {
        'BAND': band,
        'EIGHT_CONNECTEDNESS': False,
        'EXTRA': '',
        'FIELD': field,
        'INPUT': input_layer,
        'OUTPUT': output
    }
    return applyProcessingAlg("gdal","polygonize", parameters,context,feedback)

def applyExtractByAttribute(input_layer, field, output, operator=0,value='1', context=None,feedback=None):
    parameters = {
        'FIELD': field,
        'INPUT': input_layer,
        'OPERATOR': operator,  #0 =
        'VALUE': value,
        'OUTPUT': output
    }
    return applyProcessingAlg("native","extractbyattribute", parameters, context, feedback)

def applyFieldCalculator(input_layer, field, output, formula, field_length, field_precision, field_type, context=None,feedback=None):
    parameters = {
        'FIELD_LENGTH': field_length,
        'FIELD_NAME': field,
        'FIELD_PRECISION': field_precision,
        'FIELD_TYPE': field_type,
        'FORMULA':  formula,
        'INPUT': input_layer,
        'OUTPUT': output
    }
    return applyProcessingAlg("native","fieldcalculator", parameters, context, feedback)

def applyAutoIncrementField(input_layer, field, output, context=None,feedback=None):
    parameters = {
        'FIELD_NAME': field,
        'GROUP_FIELDS': [''],
        'INPUT': input_layer,
        'MODULUS': 0,
        'SORT_ASCENDING': True,
        'SORT_EXPRESSION': '',
        'SORT_NULLS_FIRST': False,
        'START': 0,
        'OUTPUT': output
    }
    return applyProcessingAlg("native","addautoincrementalfield", parameters,context,feedback)

def applyUnion(input_layer, overlay, output, overlay_fields_prefix='',context=None,feedback=None):
    parameters = {
        'INPUT': input_layer,
        'OVERLAY': overlay,
        'OVERLAY_FIELDS_PREFIX': overlay_fields_prefix,
        'OUTPUT': output
    }
    return applyProcessingAlg("native","union", parameters,context,feedback)

def applyFillNoData(input_raster, output, band=1, fill_value=1, context=None,feedback=None):
    parameters = {
        'BAND': band,
        'FILL_VALUE': fill_value,
        'INPUT': input_raster,
        'OUTPUT': output
    }
    return applyProcessingAlg("native","fillnodata", parameters,context,feedback)

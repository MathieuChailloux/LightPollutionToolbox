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

from qgis.core import (Qgis,
                       QgsProcessing,
                       QgsProcessingFeedback,
                       QgsProcessingAlgorithm,
                       QgsProcessingUtils,
                       QgsProject,
                       QgsProperty,
                       QgsFeature,
                       QgsFeatureRequest,
                       QgsField,
                       QgsProcessingContext,
                       QgsVectorLayer,
                       QgsRasterLayer,
                       QgsExpression,
                       QgsTask,
                       QgsUnitTypes)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QGuiApplication

import shutil
import os.path
import sys
import subprocess
import time

import processing

from . import utils, qgsUtils

nodata_val = '-9999'
MEMORY_LAYER_NAME = 'memory:'
# GTIFF_COPT = qgsUtils.GTIFF_COPT
GTIFF_COPT = []
gtiff_opts_pipe = '|'.join(GTIFF_COPT)
gtiff_opts_comma = ','.join(GTIFF_COPT)

gdal_calc_cmd = None
gdal_merge_cmd = None
gdal_rasterize_cmd = None
gdal_warp_cmd = None

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
def qgsTypeToInt(qgis_type,shift=False,typeList=2,defaultType=Qgis.Float32):
    if isinstance(qgis_type,Qgis.DataType):
        TYPES1 = [Qgis.Byte, Qgis.Int16, Qgis.UInt16, Qgis.Int32, Qgis.UInt32, Qgis.Float32,
                 Qgis.Float64, Qgis.CInt16, Qgis.CInt32, Qgis.CFloat32, Qgis.CFloat64]
        TYPES2 = [Qgis.Byte, Qgis.Int16, Qgis.UInt16, Qgis.UInt32, Qgis.Int32, Qgis.Float32,
                 Qgis.Float64, Qgis.CInt16, Qgis.CInt32, Qgis.CFloat32, Qgis.CFloat64]
        TYPES3 = [Qgis.Byte, Qgis.UInt16, Qgis.Int16, Qgis.UInt32, Qgis.Int32, Qgis.Float32,
                 Qgis.Float64, Qgis.CInt16, Qgis.CInt32, Qgis.CFloat32, Qgis.CFloat64]
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
            # if int_value == 0:
                # int_value = typeList.index(defaultType)
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

# Custom treatments

def selectGeomByExpression(in_layer,expr,out_path,out_name):
    #utils.info("Calling 'selectGeomByExpression' algorithm")
    start_time = time.time()
    qgsUtils.removeVectorLayer(out_path)
    if isinstance(in_layer,str):
        in_layer = qgsUtils.loadVectorLayer(in_layer)
    out_layer = qgsUtils.createLayerFromExisting(in_layer,out_name)
    orig_field = QgsField("Origin", QVariant.String)
    out_layer.dataProvider().addAttributes([orig_field])
    out_layer.updateFields()
    fields = out_layer.fields()
    out_provider = out_layer.dataProvider()
    in_name = in_layer.name()
    if expr:
        feats = in_layer.getFeatures(QgsFeatureRequest().setFilterExpression(expr))
    else:
        feats = in_layer.getFeatures(QgsFeatureRequest())
    for f in feats:
        geom = f.geometry()
        new_f = QgsFeature(fields)
        new_f.setGeometry(geom)
        new_f["Origin"] = in_layer.name()
        res = out_provider.addFeature(new_f)
        if not res:
            internal_error("addFeature failed")
    out_layer.updateExtents()
    qgsUtils.writeVectorLayer(out_layer,out_path)
    end_time = time.time()
    diff_time = end_time - start_time
    #utils.info("Call to 'selectGeomByExpression' successful"
    #           + ", performed in " + str(diff_time) + " seconds")
    
def classifByExpr(in_layer,expr,out_path,out_name):
    #utils.info("Calling 'selectGeomByExpression' algorithm")
    qgsUtils.removeVectorLayer(out_path)
    if isinstance(in_layer,str):
        in_layer = qgsUtils.loadVectorLayer(in_layer)
    out_layer = qgsUtils.createLayerFromExisting(in_layer,out_name)
    value_field = QgsField("Value", QVariant.Int)
    orig_field = QgsField("Origin", QVariant.String)
    out_layer.dataProvider().addAttributes([value_field,orig_field])
    out_layer.updateFields()
    fields = out_layer.fields()
    out_provider = out_layer.dataProvider()
    in_name = in_layer.name()
    if expr:
        feats = in_layer.getFeatures(QgsFeatureRequest().setFilterExpression(expr))
    else:
        feats = in_layer.getFeatures(QgsFeatureRequest())
    for f in feats:
        geom = f.geometry()
        new_f = QgsFeature(fields)
        new_f.setGeometry(geom)
        new_f["Value"] = 1
        new_f["Origin"] = in_layer.name()
        res = out_provider.addFeature(new_f)
        if not res:
            internal_error("addFeature failed")
    if expr:
        not_expr = "NOT(" + str(expr) + ")"
        feats = in_layer.getFeatures(QgsFeatureRequest().setFilterExpression(not_expr))
        for f in feats:
            geom = f.geometry()
            new_f = QgsFeature(fields)
            new_f.setGeometry(geom)
            new_f["Value"] = 0
            new_f["Origin"] = in_layer.name()
            res = out_provider.addFeature(new_f)
            if not res:
                internal_error("addFeature failed")
    out_layer.updateExtents()
    qgsUtils.writeVectorLayer(out_layer,out_path)

# Processing utils

def parameterAsSourceLayer(obj_alg,parameters,paramName,context,feedback=None):
    source = obj_alg.parameterAsSource(parameters,paramName,context)
    if source:
        layer = source.materialize(QgsFeatureRequest(),feedback=feedback)
    else:
        layer = None
    return source, layer
   
# Vector algorithms

def addUniqueValue(layer,fieldname,outField,out_path,assoc_path,
        context=None,feedback=None):
    parameters = { 'FIELD' : fieldname,
        'FIELD_NAME' : outField,
        'INPUT' : layer,
        'OUTPUT' : out_path,
        'SUMMARY_OUTPUT' : assoc_path }
    res = applyProcessingAlg("native","adduniquevalueindexfield",
        parameters,context=context,feedback=feedback)
    return res
    
def addIdxField(layer,outField,out_path,context=None,feedback=None):
    parameters = { 'INPUT' : layer,
        'FIELD_NAME' : outField,
        'OUTPUT' : out_path }
    res = applyProcessingAlg("native","addautoincrementalfield",
        parameters,context=context,feedback=feedback)
    return res
    
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
    # parameters = { 'DISCARD_NONMATCHING' : False,
        # 'INPUT' : in_layer,
        # 'JOIN' : join_layer,
        # 'JOIN_FIELDS' : ['flux_lampe'],
        # 'OUTPUT' : 'TEMPORARY_OUTPUT',
        # 'PREDICATE' : [0],
        # 'SUMMARIES' : [0,1,2,3,5,6] }
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
    
def joinToReportingLayer(init_layer,reporting_layer_path,out_name):
    init_pr = init_layer.dataProvider()
    out_layer = qgsUtils.createLayerFromExisting(in_layer,out_name)
    
        
def extractByExpression(in_layer,expr,out_layer,fail_out=None,context=None,feedback=None):
    #utils.checkFileExists(in_layer)
    #if out_layer:
    #    qgsUtils.removeVectorLayer(out_layer)
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
    
def selectByExpression(in_layer,expr,context=None,feedback=None):
    parameters = { 'EXPRESSION' : expr,
                   'INPUT' : in_layer,
                   'METHOD' : 0 }
    res = applyProcessingAlg("qgis","selectbyexpression",parameters,context=context,feedback=feedback)
    return res
        
def selectByLoc(source_layer,intersect_layer,method=0,predicate=[0],context=None,feedback=None):
    parameters = { 'INPUT' : source_layer,
                   'INTERSECT' : intersect_layer,
                   'METHOD' : method,
                   'PREDICATE' : predicate }
    res = applyProcessingAlg("native","selectbylocation",parameters,context=context,feedback=feedback)
    return res
    
def saveSelectedAttributes(in_layer,out_layer,context=None,feedback=None):
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    res = applyProcessingAlg("native","saveselectedfeatures",parameters,context=context,feedback=feedback)
    return res
    
def cloneLayer(layer):
    layer.selectAll()
    clone_layer = saveSelectedAttributes(layer,'memory:')
    return clone_layer
                   
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
    
def saveSelectedFeatures(in_layer,out_layer,context=None,feedback=None):
    # feedback.setProgressText("Save selected")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer }
    res = applyProcessingAlg("native","saveselectedfeatures",parameters,context,feedback)
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
def applySymDifference(in_layer,diff_layer,out_layer,grid_size=None,context=None,feedback=None):
    feedback.setProgressText("Symmetrical Difference")
    parameters = { 'INPUT' : in_layer,
                   'GRID_SIZE' : grid_size,
                   'OUTPUT' : out_layer,
                   'OVERLAY' : diff_layer }
    res = applyProcessingAlg("native","symmetricaldifference",parameters,context=context,feedback=feedback)
    return res  
    
def applyVectorClip(in_layer,clip_layer,out_layer,context=None,feedback=None):
    feedback.setProgressText("Clip")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer,
                   'OVERLAY' : clip_layer }
    res = applyProcessingAlg("qgis","clip",parameters,context,feedback)
    return res  
    
def clipVectorByExtent(in_layer,extent,out_layer,context=None,feedback=None):
    feedback.setProgressText("Clip")
    parameters = { 'INPUT' : in_layer,
                   'OUTPUT' : out_layer,
                   'EXTENT' : extent }
    res = applyProcessingAlg("gdal","clipvectorbyextent",parameters,context,feedback)
    return res
    
def applyIntersection(in_layer,clip_layer,out_layer,input_fields=[],
        clip_fields=[],context=None,feedback=None):
    feedback.setProgressText("Intersection")
    parameters = { 'INPUT' : in_layer,
                   'INPUT_FIELDS' : input_fields,
                   'OUTPUT' : out_layer,
                   'OVERLAY' : clip_layer,
                   'OVERLAY_FIELDS' : clip_fields }
    res = applyProcessingAlg("qgis","intersection",parameters,context,feedback)
    return res
    
def selectIntersection(in_layer,overlay_layer,context=None,feedback=None):
    #feedback.setProgressText("Intersection")
    parameters = { 'INPUT' : in_layer,
                   'INTERSECT' : overlay_layer,
                   'METHOD' : 0,
                   'PREDICATE' : [0] }
    res = applyProcessingAlg("native","selectbylocation",parameters,context,feedback)
    return res
    
def statsByCategories(inLayer,outLayer,categoryFields=[],valuesField=None,
        context=None,feedback=None):
    parameters = { 'INPUT' : inLayer,
        'OUTPUT' : outLayer,
        'CATEGORIES_FIELD_NAME' : categoryFields,
        'VALUES_FIELD_NAME' : valuesField }
    res = applyProcessingAlg("qgis","statisticsbycategories",parameters,
        context,feedback)
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
    
def fieldCalculator(input,field,formula,output,
        length=0,precision=0,type=0,context=None,feedback=None):

    #{ 'FIELD_LENGTH' : 0, 'FIELD_NAME' : 'test', 'FIELD_PRECISION' : 0, 'FIELD_TYPE' : 0, 'FORMULA' : '$area', 'INPUT' : 'E:/IRSTEA/IMBE_Verdon/PluginQualification/test/CLC_BO_single.gpkg', 'OUTPUT' : 'TEMPORARY_OUTPUT' }
    parameters = { 'FIELD_LENGTH' : length,
        'FIELD_NAME' : field,
        'FIELD_PRECISION' : precision,
        'FIELD_TYPE' : type,
        'FORMULA' : formula,
        'INPUT' : input,
        'OUTPUT' : output }
    res = applyProcessingAlg("native","fieldcalculator",parameters,context,feedback)
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
    
def applyPolygonizeFieldOpt(input,output,band=1,eight=False,fieldname='DN',context=None,feedback=None):
    parameters = { 'BAND' : 1,
        'EIGHT_CONNECTEDNESS' : eight,
        'EXTRA' : '',
        'FIELD' : fieldname,
        'INPUT' : input,
        'OUTPUT' : output }
    return applyProcessingAlg("gdal","polygonize",parameters,context,feedback)
    
def convertGeomType(input,type,output,context=None,feedback=None):
    parameters = { 'INPUT' : input, 'TYPE' : type, 'OUTPUT' : output }

def listUniqueValues(input,fieldname,output=None,outputHtml=None,
        context=None,feedback=None):
    params = { 'FIELDS' : [fieldname],
        'INPUT' : input,
        # 'OUTPUT' : 'TEMPORARY_OUTPUT',
        # 'OUTPUT_HTML_FILE' : 'TEMPORARY_OUTPUT' }
        'OUTPUT' : output,
        'OUTPUT_HTML_FILE' : outputHtml }
    return applyProcessingAlg("qgis","listuniquevalues",
        params,context,feedback,onlyOutput=False)
def getVectorUniqueVals(input,fieldname,context=None,feedback=None):
    unique_ret = listUniqueValues(input,fieldname,
        context=context,feedback=feedback)
    unique_values_str = unique_ret['UNIQUE_VALUES']
    unique_values = unique_values_str.split(";")
    # Cast values from str if needed
    if isinstance(input,str):
        input = qgsUtils.loadVectorLayer(input)
    input_type = input.dataProvider().fields().field(fieldname).type()
    if qgsUtils.qgisTypeIsInteger(input_type):
        feedback.pushDebugInfo("data_type = " + str(input_type))
        unique_values = [int(v) for v in unique_values]
    # Return
    return unique_values

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

def getRasterUniqueValsReport(input,context=None,feedback=None):
    # input_type = input.dataProvider().dataType(1)
    tmp_html = QgsProcessingUtils.generateTempFilename('OUTPUT_HTML_FILE.html')
    tmp_table = QgsProcessingUtils.generateTempFilename('OUTPUT_TABLE.gpkg')
    parameters = { 'BAND' : 1,
                   'INPUT' : input,
                   'OUTPUT_HTML_FILE' : tmp_html,
                   'OUTPUT_TABLE' : tmp_table }
    ret = applyProcessingAlg("native","rasterlayeruniquevaluesreport",parameters,
                             context=context,feedback=feedback,onlyOutput=False)
    return ret

def getRasterUniqueVals(input,feedback):
    feedback.pushDebugInfo("HEY")
    report = getRasterUniqueValsReport(input,feedback=feedback)
    if isinstance(input,str):
        input = qgsUtils.loadRasterLayer(input)
    input_type = input.dataProvider().dataType(1)
    tmp_table = report['OUTPUT_TABLE']
    tmp_html = report['OUTPUT_HTML_FILE']
    table_lyr = qgsUtils.loadVectorLayer(tmp_table)
    unique_vals = qgsUtils.getVectorVals(table_lyr,'value')
    feedback.pushDebugInfo("unique_vals = " + str(unique_vals))
    feedback.pushDebugInfo("data_type = " + str(input_type))
    if qgsUtils.qgisTypeIsInteger(input_type):
        feedback.pushDebugInfo("data_type = " + str(input_type))
        unique_vals = [int(v) for v in unique_vals]
    feedback.pushDebugInfo("unique_vals = " + str(unique_vals))
    feedback.setProgress(100)
    return unique_vals
    
def rasterZonalStats(vector,raster,output,prefix='_',band=1,stats=[0,1,2],context=None,feedback=None):
    parameters = { 'COLUMN_PREFIX' : prefix,
        'INPUT' : vector,
        'INPUT_RASTER' : raster,
        'OUTPUT' : output,
        'RASTER_BAND' : band,
        'STATISTICS' : stats }
    return applyProcessingAlg("native","zonalstatisticsfb",parameters,context,feedback)
    
def zonalHisto(vector,raster,output,prefix='HISTO_',band=1,context=None,feedback=None):
    parameters = { 'COLUMN_PREFIX' : prefix,
        'INPUT_RASTER' : raster,
        'INPUT_VECTOR' : vector,
        'OUTPUT' : output,
        'RASTER_BAND' : band }
    return applyProcessingAlg("native","zonalhistogram",parameters,context,feedback)
    
def applyReclassifyByTable(input,table,output,
                           nodata_val=nodata_val,out_type=Qgis.Float32,
                           boundaries_mode=1,nodata_missing=True,
                           context=None,feedback=None):
    # Types : 0 = Byte, ...
    parameters = { 'DATA_TYPE' : qgsTypeToInt(out_type,shift=True),
                   'INPUT_RASTER' : input,
                   'NODATA_FOR_MISSING' : nodata_missing,
                   'NO_DATA' : nodata_val,
                   'OUTPUT' : output,
                   'RANGE_BOUNDARIES' : boundaries_mode,
                   'RASTER_BAND' : 1,
                   'TABLE' : table }
    return applyProcessingAlg("native","reclassifybytable",parameters,context,feedback)
    
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
    
# def applyReclassifyByTableInt(input,tuples,output,nodata_val=nodata_val,context=None,feedback=None):
    # table = []
    # for k, v in tuple:
        # table.append(k)
        # table.append(k)
        # table.append(v)
    # boundaries_mode = 2
    # return applyReclassifyByTable(input,table,output,nodata_val,boundaries_mode,context,feedback)
    
"""
    GDAL RASTER ALGORITHMS
"""

# Apply rasterization on field 'field' of vector layer 'in_path'.
# Output raster layer in 'out_path'.
# Resolution set to 25 if not given.
# Extent can be given through 'extent_path'. If not, it is extracted from input layer.
# Output raster layer is loaded in QGIS if 'load_flag' is True.
def applyRasterization(in_path,out_path,extent,resolution,
                       field=None,burn_val=None,out_type=Qgis.Float32,
                       nodata_val=nodata_val,all_touch=False,overwrite=False,
                       context=None,feedback=None,options=gtiff_opts_pipe):
    TYPES = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32',
             'Float64', Qgis.CInt16, Qgis.CInt32, 'CFloat32', 'CFloat64']
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
             'Float32', 'Float64', Qgis.CInt16, Qgis.CInt32, 'CFloat32', 'CFloat64']
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
    utils.debug("parameters = " + str(parameters))
    return applyProcessingAlg("gdal","cliprasterbymasklayer",parameters,context,feedback)
    
def clipRasterAllTouched(raster_path,vector_path,dst_crs,
                         out_path=None,nodata=None,data_type=USE_INPUT_TYPE,
                         resolution=None,context=None,feedback=None):
    feedback.setProgressText("Clip raster at")
    # data type 0 = input raster type
    if isinstance(vector_path,QgsVectorLayer):
        vector_path = qgsUtils.pathOfLayer(vector_path)
    extra_params = "-cutline " + str(vector_path)
    extra_params += " -crop_to_cutline -wo CUTLINE_ALL_TOUCHED=True"
    parameters = { 'DATA_TYPE' : qgsTypeToInt(data_type),
                   'INPUT' : raster_path,
                   'NODATA' : nodata,
                   'OUTPUT' : out_path,
                   'RESAMPLING' : 0,
                   'TARGET_CRS' : dst_crs,
                   'TARGET_RESOLUTION' : resolution,
                   'OPTIONS' : gtiff_opts_pipe,
                   'EXTRA' : extra_params }
    return applyProcessingAlg("gdal","warpreproject",parameters,context,feedback)
    

    
def applyMergeRaster(files,output,nodata_val=nodata_val,out_type=Qgis.Float32,
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
# def applyMergeRaster2(files,output,nodata_val=nodata_val,out_type=Qgis.Float32,
#                      nodata_input=None,pct=False,separate=False,context=None,feedback=None):
#     TYPES = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64', 'CInt16', 'CInt32', 'CFloat32', 'CFloat64']
#     feedback.setProgressText("Merge raster")
#     parameters = {
#             'DATA_TYPE': qgsTypeToInt(out_type,shift=True),
#             'EXTRA': '',
#             'INPUT': files,
#             'NODATA_INPUT': nodata_input,
#             'NODATA_OUTPUT': nodata_val,
#             'OPTIONS' : gtiff_opts_pipe,
#             'PCT': pct,
#             'SEPARATE': separate,
#             'OUTPUT': 'TEMPORARY_OUTPUT'
#         }
#     mergedPath = applyProcessingAlg("gdal","merge",parameters,context,feedback)
#     shutil.copyfile(mergedPath,output)
#     return mergedPath
    
def applyRasterCalcNative(layers,expr,output,
        extent=None,cellSize=None,crs=None,
        context=None,feedback=None):
    parameters = {
        'CELL_SIZE' : cellSize,
        'CRS' : crs,
        'EXPRESSION' : expr,
        'EXTENT' : extent,
        'LAYERS' : layers,
        'OUTPUT' : output }
    return applyProcessingAlg("native","rastercalc",parameters,
        context,feedback)
                   
def applyRasterCalcProc(input_a,output,expr,
                    nodata_val=nodata_val,out_type=Qgis.Float32,
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
                    nodata_val=nodata_val,out_type=Qgis.Float32,
                    context=None,feedback=None):
    out_type = qgsTypeToInt(out_type,shift=True)
    TYPE = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64']
    type_str = TYPE[out_type]
    if isinstance(input_a,QgsRasterLayer):
        input_a = qgsUtils.pathOfLayer(input_a)
    #applyGdalCalc(input_a,output,expr,type=type_str,nodata=nodata_val)
    applyRasterCalcProc(input_a,output,expr,nodata_val=nodata_val,
        out_type=out_type,context=context,feedback=feedback)
    return output
    
def applyRasterCalcLT(input,output,max_val,
                      nodata_val=nodata_val,out_type=Qgis.Float32,
                      context=None,feedback=None):
    expr = "less(A," + str(max_val) + ")*A+less_equal(" + str(max_val) + ",A)*" + str(nodata_val)
    return applyRasterCalc(input,output,expr,nodata_val,out_type,
               context=context,feedback=feedback)
    
def applyRasterCalcLE(input,output,max_val,
                      nodata_val=nodata_val,out_type=Qgis.Float32,
                      context=None,feedback=None):
    expr = "less_equal(A," + str(max_val) + ")*A+less(" + str(max_val) + ",A)*" + str(nodata_val)
    return applyRasterCalc(input,output,expr,nodata_val,out_type,
               context=context,feedback=feedback)
    
def applyRasterCalcAB(input_a,input_b,output,expr,
                    nodata_val=nodata_val,out_type=Qgis.Float32,
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
                    nodata_val=None,out_type=Qgis.Float32,
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
    
def applyRasterCalcAB_ABNull(input_a,input_b,output,expr,
                    nodata_val=nodata_val,out_type=Qgis.Float32,
                    context=None,feedback=None):
    TYPE = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64']
    if os.path.isfile(output):
        qgsUtils.removeRaster(output)
    tmp_no_data_val = -998
    nd_str = str(tmp_no_data_val)
    nonull_a = QgsProcessingUtils.generateTempFilename("nonull_a.tif")
    nonull_b = QgsProcessingUtils.generateTempFilename("nonull_b.tif")
    nonull_ab = QgsProcessingUtils.generateTempFilename("nonull_ab.tif")
    nonull_reset = QgsProcessingUtils.generateTempFilename("nonull_reset.tif")
    applyRNull(input_a,tmp_no_data_val,nonull_a,context=context,feedback=feedback)
    applyRNull(input_b,tmp_no_data_val,nonull_b,context=context,feedback=feedback)
    # a_nodata = str(input_a.dataProvider().sourceNoDataValue(1))
    # b_nodata = str(input_b.dataProvider().sourceNoDataValue(1))
    expr_wrap = "equal(A," + nd_str + ") * B "
    expr_wrap += " + logical_and(not_equal(A," + nd_str + "),equal(B," + nd_str + ")) * A"
    expr_wrap += " + logical_and(not_equal(A," + nd_str + "),not_equal(B," + nd_str +")) * (" + str(expr) + ")"
    parameters = { 'BAND_A' : 1,
                   'BAND_B' : 1,
                   'FORMULA' : expr_wrap,
                   'INPUT_A' : nonull_a,
                   'INPUT_B' : nonull_b,
                   'NO_DATA' : nodata_val,
                   'OUTPUT' : nonull_ab,
                   'OPTIONS' : gtiff_opts_pipe,
                   'RTYPE' : qgsTypeToInt(out_type,shift=True) }
    applyProcessingAlg("gdal","rastercalculator",parameters,
        context=context,feedback=feedback)
    reset_nodata_expr = '(A==' + str(tmp_no_data_val) + ')*' + str(nodata_val)
    reset_nodata_expr += '+(A!=' + str(tmp_no_data_val) + ')*A'
    applyRasterCalc(nonull_ab,output,reset_nodata_expr,context=context,feedback=feedback)
    return output
    # return applyRSetNull(nonull_reset,nodata_val,output)
                       
def applyRasterCalcMult(input_a,input_b,output,
                        nodata_val=nodata_val,out_type=Qgis.Float32,
                        context=None,feedback=None):
    expr = "A*B"
    return applyRasterCalcAB(input_a,input_b,output,expr,
                             nodata_val=nodata_val,out_type=out_type,
                             context=context,feedback=feedback)
                   
def applyRasterCalcMin(input_a,input_b,output,
                       nodata_val=nodata_val,out_type=Qgis.Float32,
                       context=None,feedback=None):
    min = qgsUtils.getRastersMinMax([input_a,input_b])
    expr = 'A*less_equal(A,B) + B*less(B,A)'
    return applyRasterCalcAB_ABNull(input_a,input_b,output,expr,nodata_val=nodata_val,
                out_type=out_type,context=context,feedback=feedback)
                   
def applyRasterCalcMax(input_a,input_b,output,
                       nodata_val=nodata_val,out_type=Qgis.Float32,
                       context=None,feedback=None):
    expr = 'B*less_equal(A,B) + A*less(B,A) '
    return applyRasterCalcAB_ABNull(input_a,input_b,output,expr,nodata_val=nodata_val,
                out_type=out_type,context=context,feedback=feedback)
  
def applyProximity(input,output,classes='',band=1,units=0,context=None,feedback=None):
    # { 'BAND' : 1, 'DATA_TYPE' : 5, 'EXTRA' : '', 'INPUT' : 'E:/IRSTEA/IMBE_Verdon/data/clc_lines_raster.tif', 'MAX_DISTANCE' : 0, 'NODATA' : 0, 'OPTIONS' : '', 'OUTPUT' : 'TEMPORARY_OUTPUT', 'REPLACE' : 0, 'UNITS' : 0, 'VALUES' : '1,2,3,4,5' }
    parameters = {
        'INPUT' : input,
        'OUTPUT' : output,
        'VALUES' : classes,
        'BAND' : band,
        'OPTIONS' : gtiff_opts_pipe,
        'UNITS' : units }
    return applyProcessingAlg("gdal","proximity",parameters,context,feedback)
  
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
    GRASS ALGORITHMS
"""

def applyVRandom(vector_layer,nb_points,output,context=None,feedback=None):
    parameters = { 'npoints' : nb_points,
        'output' : output,
        'restrict' : vector_layer }
    return applyGrassAlg("v.random",parameters,context,feedback)

# { '-a' : False, '-z' : False, 'GRASS_MIN_AREA_PARAMETER' : 0.0001, 'GRASS_OUTPUT_TYPE_PARAMETER' : 0, 'GRASS_REGION_PARAMETER' : None, 'GRASS_SNAP_TOLERANCE_PARAMETER' : -1, 'GRASS_VECTOR_DSCO' : '', 'GRASS_VECTOR_EXPORT_NOCAT' : False, 'GRASS_VECTOR_LCO' : '', 'column' : '', 'column_type' : None, 'npoints' : 100, 'output' : 'TEMPORARY_OUTPUT', 'restrict' : 'E:/IRSTEA/BioDispersal/Tests/BousquetOrbExtended/Source/Reservoirs/RBP_PRAIRIE.shp', 'seed' : None, 'where' : '', 'zmax' : None, 'zmin' : None }

# Apply raster calculator from expression 'expr'.
# Calculation is made on a single file and a signled band renamed 'A'.
# Output format is Integer32.
def applyResample(in_path,out_path,context=None,feedback=None):
    parameters = {'input' : in_path,
                  'output' : out_path,
                  '--overwrite' : True,
                  'GRASS_REGION_CELLSIZE_PARAMETER' : 50,
                  'GRASS_SNAP_TOLERANCE_PARAMETER' : -1,
                  'GRASS_RASTER_FORMAT_OPT': gtiff_opts_comma,
                  'GRASS_MIN_AREA_PARAMETER' : 0}
    return applyGrassAlg("r.resample",parameters,context,feedback)
    
def applyReclassGdal(in_path,out_path,rules_file,title,context=None,feedback=None):
    parameters = {'input' : in_path,
                  'output' : out_path,
                  'rules' : rules_file,
                  'title' : title,
                  'GRASS_REGION_CELLSIZE_PARAMETER' : 50,
                  'GRASS_SNAP_TOLERANCE_PARAMETER' : -1,
                  'GRASS_RASTER_FORMAT_OPT': gtiff_opts_comma,
                  'GRASS_MIN_AREA_PARAMETER' : 0}
    return applyGrassAlg("r.reclass",parameters,context,feedback)
    
def applyRNull(in_path,new_val,out_path,context=None,feedback=None):
    parameters = { 'map' : in_path,
                   'null' : str(new_val),
                   'output' : out_path }
    return applyGrassAlg("r.null",parameters,context,feedback)
    
def applyRSetNull(in_path,new_val,out_path,context=None,feedback=None):
    parameters = { 'map' : in_path,
                   'setnull' : str(new_val),
                   'output' : out_path }
    return applyGrassAlg("r.null",parameters,context,feedback)
    
def applyRBuffer(in_path,buffer_vals,out_path,context=None,feedback=None):
    utils.checkFileExists(in_path,"Buffer input layer ")
    distances_str = ""
    for v in buffer_vals:
        if distances_str != "":
            distances_str += ","
        distances_str += str(v)
    parameters = { 'input' : in_path,
                    'output' : out_path,
                    'distances' : distances_str, #"0,100,200",
                    'units' : 0, # 0 = meters ?
                    #'memory' : 5000,
                    'GRASS_RASTER_FORMAT_META' : '',
                    'GRASS_RASTER_FORMAT_OPT': gtiff_opts_comma,
                    #'GRASS_REGION_CELLSIZE_PARAMETER' : 25,
                    'GRASS_REGION_PARAMETER' : None,
                    '-z' : False,
                    '--type' : 'Int32',
                    '--overwrite' : False}
    return applyGrassAlg("r.buffer.lowmem",parameters,context,feedback)
    
def applyRCost(start_path,cost_path,cost,out_path,context=None,feedback=None):
    utils.checkFileExists(start_path,"Dispersion Start Layer ")
    utils.checkFileExists(cost_path,"Dispersion Permeability Raster ")
    parameters = { 'input' : cost_path,
                    'start_raster' : start_path,
                    'max_cost' : float(cost),
                    'null_cost' : None,
                    'output' : out_path,
                    'start_points' : None,
                    'stop_points' : None,
                    'start_coordinates' : None,
                    'stop_coordinates' : None,
                    'outir' : None,
                    'memory' : 5000,
                    'GRASS_MIN_AREA_PARAMETER' : 0.0001, 
                    'GRASS_RASTER_FORMAT_META' : '',
                    'GRASS_RASTER_FORMAT_OPT': gtiff_opts_comma,
                    #'GRASS_REGION_CELLSIZE_PARAMETER' : 0,
                    'GRASS_REGION_PARAMETER' : None,
                    'GRASS_SNAP_TOLERANCE_PARAMETER' : -1,
                    '-k' : False,
                    '-n' : True,
                    '-r' : True,
                    '-i' : False,
                    '-b' : False,
                    '--overwrite' : True}
    return applyGrassAlg("r.cost",parameters,context,feedback)
    
def applyRCostFilterMaxCost(start_path,cost_path,cost,out_path,context=None,feedback=None):
    tmp_path = utils.mkTmpPath(out_path,suffix="_disp_tmp")
    if os.path.isfile(tmp_path):
        qgsUtils.removeRaster(tmp_path)
    applyRCost(start_path,cost_path,cost,tmp_path,context=context,feedback=feedback)
    applyRasterCalcLE(tmp_path,out_path,cost,context=context,feedback=feedback)
    
    
def applyRSeries(layers,aggr_func,output,range=None,context=None,feedback=None):
    # aggre_func : 0=average, 1=count, 2=median, 3=mode, 4=minimum, 6=maximum, ...
    parameters = { 
                   '-n' : False,
                   '-z' : False,
                   'GRASS_RASTER_FORMAT_META' : '',
                   'GRASS_RASTER_FORMAT_OPT': gtiff_opts_comma,
                   'GRASS_REGION_CELLSIZE_PARAMETER' : 0,
                   'GRASS_REGION_PARAMETER' : None,
                   'input' : layers,
                   'method' : [aggr_func],
                   'output' : output,
                   'range' : range,
                    '--overwrite' : True }
    applyGrassAlg("r.series",parameters,context,feedback)
    #qgsUtils.loadRasterLayer(output,loadProject=True)
    return output

    
"""
    GDAL COMMANDS (legacy)
"""
    
# Apply rasterization on field 'field' of vector layer 'in_path'.
# Output raster layer in 'out_path'.
# Resolution set to 25 if not given.
# Extent can be given through 'extent_path'. If not, it is extracted from input layer.
# Output raster layer is loaded in QGIS if 'load_flag' is True.
def applyRasterizationCmd(in_path,field,out_path,extent_path,
                       resolution=None,load_flag=False,to_byte=False,
                       more_args=[]):
    utils.debug("applyRasterizationCmd")
    in_layer = qgsUtils.loadVectorLayer(in_path)
    if extent_path:
        extent_layer = qgsUtils.loadLayer(extent_path)
    else:
        extent_layer = qgsUtils.loadVectorLayer(in_path)
    extent = extent_layer.extent()
    #extent_crs = qgsUtils.getLayerCrsStr(extent_layer)
    extent_crs = extent_layer.crs()
    #utils.internal_error("TODO : params refactoring needed")
    #transformed_extent = params.params.getBoundingBox(extent,extent_crs)
    transformed_extent = extent
    x_min = transformed_extent.xMinimum()
    x_max = transformed_extent.xMaximum()
    y_min = transformed_extent.yMinimum()
    y_max = transformed_extent.yMaximum()
    utils.debug("resolution  = " + str(resolution))
    if resolution == 0.0:
        utils.user_error("Empty resolution")
    parameters = [gdal_rasterize_cmd,
                  '-at',
                  '-te',str(x_min),str(y_min),str(x_max),str(y_max),
                  #'-ts', str(width), str(height),
                  '-tr', str(resolution), str(resolution),
                  #'-ot','Int32',
                  #'-a_srs','epsg:2154',
                  '-of','GTiff']
                  #'-a_nodata',nodata_val]
    if to_byte:
        parameters.extend(['-ot', 'Int16','-a_nodata',nodata_val])
    if field == "geom":
        parameters.extend(['-burn', '1'])
    else:
        parameters.extend(['-a',field])
    for opt in GTIFF_COPT:
        parameters.extend(['-co', opt])
    parameters.extend(more_args)
    parameters.extend([in_path,out_path])
    utils.debug("rasterization cmd = " + str(parameters))
    p = subprocess.Popen(parameters,stderr=subprocess.PIPE)
    out,err = p.communicate()
    utils.debug(str(p.args))
    if out:
        utils.info(str(out))
    if err:
        utils.user_error(str(err))
    elif load_flag:
        res_layer = qgsUtils.loadRasterLayer(out_path)
        QgsProject.instance().addMapLayer(res_layer)
        
        
# TODO
def applyWarpGdal(in_path,out_path,resampling_mode,
                  crs=None,resolution=None,extent_path=None,
                  load_flag=False,to_byte=False):
    utils.debug("qgsTreatments.applyWarpGdal")
    in_layer = qgsUtils.loadRasterLayer(in_path)
    if extent_path:
        utils.debug("extent_path = " + str(extent_path))
        extent_layer = qgsUtils.loadLayer(extent_path)
    else:
        extent_layer = in_layer
    extent = extent_layer.extent()
    extent_crs = extent_layer.crs()
    utils.internal_error("TODO : params refactoring")
    transformed_extent = params.paramsModel.getBoundingBox(extent,extent_crs)
    x_min = transformed_extent.xMinimum()
    x_max = transformed_extent.xMaximum()
    y_min = transformed_extent.yMinimum()
    y_max = transformed_extent.yMaximum()
    if not resolution:
        resolution = in_layer.rasterUnitsPerPixelX()
        utils.warn("Setting rasterization resolution to " + str(resolution))
    #width = int((x_max - x_min) / float(resolution))
    #height = int((y_max - y_min) / float(resolution))
    in_crs = qgsUtils.getLayerCrsStr(in_layer)
    extent_crs = qgsUtils.getLayerCrsStr(extent_layer)
    cmd_args = [gdal_warp_cmd,
                '-s_srs',in_crs,
                '-t_srs',crs.authid(),
                '-te',str(x_min),str(y_min),str(x_max),str(y_max),
                #'-te_srs',extent_crs,
                #'-ts', str(width), str(height),
                '-tr', str(resolution), str(resolution),
                #'-dstnodata',nodata_val,
                #'-ot','Int16',
                '-overwrite']
    for opt in GTIFF_COPT:
        cmd_args.extend(['-co', opt])
    if resampling_mode:
        cmd_args.extend(['-r', resampling_mode])
    if to_byte:
        cmd_args.extend(['-dstnodata', nodata_val])
        cmd_args.extend(['-ot','Int16'])
    #cmd_args += more_args
    cmd_args += [in_path, out_path]
    utils.executeCmd(cmd_args)
    if load_flag:
        res_layer = qgsUtils.loadRasterLayer(out_path)
        QgsProject.instance().addMapLayer(res_layer)
        
# TO TEST
def applyReclassProcessing(in_path,out_path,rules_file,title):
    parameters = {'input' : in_path,
                  'output' : out_path,
                  'rules' : rules_file,
                  'title' : title,
                   'GRASS_RASTER_FORMAT_OPT': gtiff_opts_comma,
                   'GRASS_REGION_CELLSIZE_PARAMETER' : 50,
                   'GRASS_SNAP_TOLERANCE_PARAMETER' : -1,
                   'GRASS_MIN_AREA_PARAMETER' : 0}
    feedback = QgsProcessingFeedback()
    try:
        processing.run("grass7:r.reclass",parameters,feedback=feedback)
        utils.debug ("call to r.cost successful")
    except Exception as e:
        utils.warn ("Failed to call r.reclass : " + str(e))
        raise e
    finally:
        utils.debug("End reclass")
        
# Apply raster calculator from expression 'expr'.
# Calculation is made on a single file and a signled band renamed 'A'.
# Output format is Integer32.
def applyGdalCalc(in_path,out_path,expr,type='Int32',nodata=nodata_val,
        load_flag=False,more_args=[]):
    # global gdal_calc_cmd
    utils.debug("qgsTreatments.applyGdalCalc(" + str(expr) + ")")
    if os.path.isfile(out_path):
        qgsUtils.removeRaster(out_path)
    #cmd_args = ['gdal_calc.bat',
    if utils.platform_sys:
        cmd_args = ['gdal_calc.bat']
    else:
        cmd_args = ['gdal_calc.py']
    # gdal_calc_cmd = 'gdal_calc.bat' if utils.platform_sys == 'Windows' else 'gdal_calc.py'
    utils.debug("cmd_args commnad = " + str(cmd_args))
    cmd_args.extend([
                '-A', in_path,
                '--type=' + str(type),
                '--outfile=' + out_path,
                '--NoDataValue=' + str(nodata),
                '--overwrite'])
    cmd_args.extend(['--co', " ".join(GTIFF_COPT)])
    cmd_args.extend(more_args)
    expr_opt = '--calc=' + expr
    # expr_opt = '--calc="A*2"'
    cmd_args.append(expr_opt)
    utils.executeCmd(cmd_args)
    if load_flag:
        res_layer = qgsUtils.loadRasterLayer(out_path)
        QgsProject.instance().addMapLayer(res_layer)
        
# Filters input raster 'in_path' to keep values inferior to 'max_val' 
# in output raster 'out_path'.
def applyFilterGdalFromMaxVal(in_path,out_path,max_val,load_flag=False):
    utils.debug("qgsTreatments.applyReclassGdalFromMaxVal(" + str(max_val) + ")")
    expr = ('(A*less_equal(A,' + str(max_val) + ')*less_equal(0,A))'
        + '+(' + str(nodata_val) + '*less(' + str(max_val) + ',A))'
        + '+(' + str(nodata_val) + '*less(A,0))')
    applyGdalCalc(in_path,out_path,expr,load_flag,more_args=['--type=Float32'])
    
# Applies reclassification from 'in_path' to 'out_path' according to 'reclass_dict'.
# Dictionary contains associations of type {old_val -> new_val}.
# Pixels of value 'old_val' are set to 'new_val' value.
def applyReclassGdalFromDict(in_path,out_path,reclass_dict,load_flag=False):
    utils.debug("qgsTreatments.applyReclassGdalFromDict(" + str(reclass_dict) + ")")
    expr = ''
    for old_cls,new_cls in reclass_dict.items():
        if expr != '':
            expr += '+'
        expr += str(new_cls) + '*(A==' + str(old_cls)+ ')'
    applyGdalCalc(in_path,out_path,expr,load_flag)
    
def applyGdalCalcAB_ANull(in_path1,in_path2,out_path,expr,load_flag=False):
    utils.debug("qgsTreatments.applyGdalCalcAB")
    if os.path.isfile(out_path):
        qgsUtils.removeRaster(out_path)
    cmd_args = [gdal_calc_cmd,
                '-A', in_path1,
                '-B', in_path2,
                #'--type=Int32',
                '--NoDataValue='+nodata_val,
                '--overwrite',
                '--outfile='+out_path]
    expr_opt = '--calc=' + str(expr)
    cmd_args.extend(['--co', " ".join(GTIFF_COPT)])
    cmd_args.append(expr_opt)
    utils.executeCmd(cmd_args)
    if load_flag:
        res_layer = qgsUtils.loadRasterLayer(out_path)
        QgsProject.instance().addMapLayer(res_layer)
    
# Creates raster 'out_path' from 'in_path1', 'in_path2' and 'expr'.
# def applyGdalCalcAB(in_path1,in_path2,out_path,expr,load_flag=False):
    # utils.debug("qgsTreatments.applyGdalCalcAB")
    # if os.path.isfile(out_path):
        # qgsUtils.removeRaster(out_path)
    # tmp_no_data_val = -1
    # nonull_p1 = utils.mkTmpPath(in_path1,suffix="_nonull")
    # nonull_p2 = utils.mkTmpPath(in_path2,suffix="_nonull")
    # nonull_out = utils.mkTmpPath(out_path,suffix="_nonull")
    # nonull_out_tmp = utils.mkTmpPath(nonull_out,suffix="_tmp")
    # applyRNull(in_path1,tmp_no_data_val,nonull_p1)
    # applyRNull(in_path2,tmp_no_data_val,nonull_p2)
    # cmd_args = [gdal_calc_cmd,
                # '-A', nonull_p1,
                # '-B', nonull_p2,
                # '--NoDataValue='+nodata_val,
                # '--overwrite',
                # '--outfile='+nonull_out]
    # expr_opt = '--calc=' + str(expr)
    # cmd_args.append(expr_opt)
    # utils.executeCmd(cmd_args)
    # reset_nodata_expr = '(A==' + str(tmp_no_data_val) + ')*' + str(nodata_val)
    # reset_nodata_expr += '+(A!=' + str(tmp_no_data_val) + ')*A'
    # applyGdalCalc(nonull_out,nonull_out_tmp,reset_nodata_expr)
    # applyRSetNull(nonull_out_tmp,nodata_val,out_path)
    # remove_tmp_flag = not utils.debug_flag
    # if remove_tmp_flag:
        # qgsUtils.removeRaster(nonull_p1)
        # qgsUtils.removeRaster(nonull_p2)
        # qgsUtils.removeRaster(nonull_out)
        # qgsUtils.removeRaster(nonull_out_tmp)
    # if load_flag:
        # res_layer = qgsUtils.loadRasterLayer(out_path)
        # QgsProject.instance().addMapLayer(res_layer)
    
# Applies ponderation on 'in_path1' according to 'in_path2' values.
# Result stored in 'out_path'.
def applyPonderationGdal(a_path,b_path,out_path,pos_values=False):
    utils.debug("qgsTreatments.applyPonderationGdal")
    if os.path.isfile(out_path):
        qgsUtils.removeRaster(out_path)
    cmd_args = [gdal_calc_cmd,
                '-A', a_path,
                '-B', b_path,
                #'--type=Int32',
                '--NoDataValue='+nodata_val,
                '--overwrite',
                '--outfile='+out_path]
    if pos_values:
        expr_opt = '--calc=A*B*less_equal(0,A)*less_equal(0,B)'
    else:
        expr_opt = '--calc=A*B'
    cmd_args.extend(['--co', " ".join(GTIFF_COPT)])
    cmd_args.append(expr_opt)
    utils.executeCmd(cmd_args)
    res_layer = qgsUtils.loadRasterLayer(out_path)
    QgsProject.instance().addMapLayer(res_layer)
    
# Creates raster 'out_path' keeping maximum value from 'in_path1' and 'in_path2'.
# def applyMaxGdal(in_path1,in_path2,out_path,load_flag=False):
    # utils.debug("qgsTreatments.applyMaxGdal")
    # expr = 'B*less_equal(A,B) + A*less(B,A)'
    # applyGdalCalcAB(in_path1,in_path2,out_path,expr,load_flag)
    
# Creates raster 'out_path' keeping maximum value from 'in_path1' and 'in_path2'.
# def applyMinGdal(in_path1,in_path2,out_path,load_flag=False):
    # utils.debug("qgsTreatments.applyMinGdal")
    # expr = 'A*less_equal(A,B) + B*less(B,A)'
    # applyGdalCalcAB(in_path1,in_path2,out_path,expr,load_flag)
                 
        
def applyGdalMerge(files,out_path,load_flag=False):
    cmd_args = [gdal_merge_cmd,
                '-o', out_path,
                '-of', 'GTiff',
                '-ot','Int32',
                '-n', nodata_val,
                '-a_nodata', nodata_val]
    cmd_args.extend(['--co', " ".join(GTIFF_COPT)])
    cmd_args += files
    utils.executeCmd(cmd_args)
    if load_flag:
        res_layer = qgsUtils.loadRasterLayer(out_path)
        QgsProject.instance().addMapLayer(res_layer)
        
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

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
    Useful functions to perform rendering style operations.
"""

import random

from PyQt5.QtGui import QColor
from qgis.core import (QgsColorRampShader,
                       QgsRasterShader,
                       QgsColorBrewerColorRamp,
                       QgsGradientColorRamp,
                       QgsCptCityColorRamp,
                       QgsPresetSchemeColorRamp,
                       QgsRasterBandStats,
                       QgsPalettedRasterRenderer,
                       QgsSingleBandPseudoColorRenderer,
                       QgsGraduatedSymbolRenderer,
                       QgsFillSymbol,
                       QgsStyle,
                       QgsSymbol,
                       QgsSimpleFillSymbolLayer,
                       QgsRendererCategory,
                       QgsCategorizedSymbolRenderer,
                       QgsRendererRange,
                       QgsRenderContext)
                       
from . import utils, qgsUtils

redHex = '#ff0000'
yellowHex = '#ffff00'
greenHex = '#00ff00'
redCol = QColor(redHex)
yellowCol = QColor(yellowHex)
greenCol = QColor(greenHex)

singleColorRampList = [ 'Blues', 'Greens', 'Oranges', 'Purples', 'Reds' ]

colorsIndPol = ['#1A9641', '#8ACC62', '#DBF09E','#FEDF9A', '#F59053', '#D7191C']
valuesIndPol = [0,1,2,3,4,5]

def getDefaultStyle():
    return QgsStyle.defaultStyle()
    
# Color utilities
    
def getPresetGnYlRd():
    colors = [redCol,yellowCol,greenCol]
    colorRamp = QgsPresetSchemeColorRamp(colors=colors)
    return colorRamp
    
def getColorBrewColorRampGnYlRd():
    colorRamp = QgsColorBrewerColorRamp(schemeName='RdYlGn',inverted=True)
    return colorRamp
    
def mkColorRamp(color,invert=False):
    style = getDefaultStyle()
    colorRamp = style.colorRamp(color)
    if invert:
        colorRamp.invert()
    return colorRamp
    
def getGradientColorRampRdYlGn(invert=True):
    return mkColorRamp('RdYlGn',invert=invert)
    
def getRandomSingleColorRamp():
    rampName = random.choice(singleColorRampList)
    return mkColorRamp(rampName,invert=True)  
    
def setRenderer(layer,renderer):
    if not renderer:
        utils.internal_error("Could not create renderer")
    layer.setRenderer(renderer)
    utils.info("about to repaint")
    layer.triggerRepaint()    
    
# Vector utilities

def mkGraduatedRenderer(layer,fieldname,color_ramp,nb_classes=5,classif_method=QgsGraduatedSymbolRenderer.Jenks):
    # classif = QgsClassificationQuantile()
    # classes = classif.classes(layer,fieldname,nb_classes)
    renderer = QgsGraduatedSymbolRenderer(attrName=fieldname)
    renderer.setSourceColorRamp(color_ramp)
    renderer.updateClasses(layer,classif_method,nb_classes)
    # renderer.setGraduatedMethod(QgsGraduatedSymbolRenderer.GraduatedColor)
    # renderer.setClassificationMethod(classif)
    return renderer
    
def setGraduatedStyle(layer,fieldname,color_ramp_name,invert_ramp=False,
        classif_method=QgsGraduatedSymbolRenderer.Jenks,invert_ranges=False):
    color_ramp = mkColorRamp(color_ramp_name,invert=invert_ramp)
    renderer = mkGraduatedRenderer(layer,fieldname,color_ramp,classif_method=classif_method)
    ranges = renderer.ranges()
    low1, low2 = ranges[0].lowerValue(), ranges[-1].lowerValue()
    if invert_ranges and low1 < low2:
        nb_ranges = len(ranges)
        loop_range = range(0,nb_ranges)
        for i in loop_range:
            renderer.moveClass(0,nb_ranges-(i+1))
    setRenderer(layer,renderer)
    
    
def setGreenGraduatedStyle(layer,fieldname):
    setGraduatedStyle(layer,fieldname,'Greens')
    # color_ramp = mkColorRamp('Greens')
    # renderer = mkGraduatedRenderer(layer,fieldname,color_ramp,classif_method=classif_method)
    # setRenderer(layer,renderer)
    
def setRdYlGnGraduatedStyle(layer,fieldname,invert_ramp=False,
        classif_method=QgsGraduatedSymbolRenderer.Jenks,invert_ranges=False):
    setGraduatedStyle(layer,fieldname,'RdYlGn',invert_ramp=invert_ramp,
        classif_method=classif_method,invert_ranges=invert_ranges)
    # color_ramp = mkColorRamp('RdYlGn')
    # renderer = mkGraduatedRenderer(layer,fieldname,color_ramp,classif_method=classif_method)
    # setRenderer(layer,renderer)
    
def setCustomClasses(layer,renderer,class_bounds):
    nb_bounds = len(class_bounds)
    renderer.updateClasses(layer,nb_bounds)
    for idx, b in enumerate(class_bounds):
        if idx > 0:
            renderer.updateRangeUpperValue(idx-1,b)
        renderer.updateRangeLowerValue(idx,b)
        
def setCustomClasses2(layer,fieldname,color_ramp,class_bounds):
    nb_bounds = len(class_bounds)
    nb_classes = nb_bounds + 1
    renderer = mkGraduatedRenderer(layer,fieldname,color_ramp,nb_classes=nb_classes)
    renderer.updateClasses(layer,nb_classes)
    for idx, b in enumerate(class_bounds,1):
        renderer.updateRangeUpperValue(idx - 1,b)
        renderer.updateRangeLowerValue(idx,b)
    setRenderer(layer,renderer)
    
def setCustomClassesDSFL(layer,fieldname):
    class_bounds = [0,10,20,25,35]
    color_ramp = getGradientColorRampRdYlGn()
    renderer = mkGraduatedRenderer(layer,fieldname,color_ramp,nb_classes=5)
    setCustomClasses(layer,renderer,class_bounds)
    setRenderer(layer,renderer)

def setCustomClassesInd_Pol_Category(layer,fieldname,class_bounds):
    categories = []
    for i in range(len(class_bounds)):
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        layer_style = {}
        layer_style['color'] = colorsIndPol[i]
        symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
        symbol_layer.setStrokeStyle(0) # no border
        if symbol_layer is not None:
            symbol.changeSymbolLayer(0, symbol_layer)
        category = QgsRendererCategory(class_bounds[i],symbol,str(class_bounds[i]))
        categories.append(category)
    renderer = QgsCategorizedSymbolRenderer(fieldname, categories)
    setRenderer(layer,renderer)

def setCustomClassesInd_Pol_Graduate(layer,fieldname,class_bounds, round_decimal=0):
    categories = []
    for i in range(len(class_bounds)):
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        layer_style = {}
        layer_style['color'] = colorsIndPol[i]
        symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
        symbol_layer.setStrokeStyle(0) # no border
        if symbol_layer is not None:
            symbol.changeSymbolLayer(0, symbol_layer)
        if i == len(class_bounds)-1: # dernier élément
            maxValue = layer.maximumValue(layer.fields().indexOf(fieldname))
            category = QgsRendererRange(class_bounds[i],maxValue,symbol,"> "+str(round(class_bounds[i],round_decimal)))
        else:
            category = QgsRendererRange(class_bounds[i],class_bounds[i+1],symbol,str(round(class_bounds[i],round_decimal))+" - "+str(round(class_bounds[i+1],round_decimal)))
        categories.append(category)
    renderer = QgsGraduatedSymbolRenderer(fieldname, categories)
    setRenderer(layer,renderer)    

def getQuantileBounds(layer, fieldname, nb_classes=5,classif_method=QgsGraduatedSymbolRenderer.Quantile, SupZero=True, lastBounds=None, round_decimal=0):
    if SupZero:
        layer.setSubsetString('"'+fieldname+'">0')
    color_ramp = mkColorRamp('RdYlGn',invert=True)
    renderer = mkGraduatedRenderer(layer,fieldname,color_ramp, nb_classes, classif_method)
    bounds = []
    for r in renderer.ranges():
        if round_decimal > 0:
            bounds.append(round((r.lowerValue()),round_decimal))
        else: # pour enlever les .0
            bounds.append(round((r.lowerValue())))
    
    if SupZero:
        layer.setSubsetString('')
        bounds.pop(0) # on enlève la première limite basse (index 0), qui sera remplacée par le seuil 0
        bounds = [0,0]+bounds # on ajoute 0 ,0 comme premières limites pour isoler ces valeurs
    
    if lastBounds: # remplacement du dernier seuil
        bounds.pop() # en enlève le dernier seul
        
        bounds_to_remove = [] # on supprime les seuils intermédaires supérieurs au seuil max
        for b in bounds:
            if b > lastBounds:
                bounds_to_remove.append(b)
        for btr in bounds_to_remove:
            bounds.remove(btr)
            
        bounds.append(round(lastBounds)) # ajoute le dernier seuil en paramètre
    
        
    return bounds

def setRdYlGnGraduatedStyle2(layer,fieldname,nb_classes=5,classif_method=QgsGraduatedSymbolRenderer.Quantile):
    color_ramp = mkColorRamp('RdYlGn',invert=True)
    renderer = mkGraduatedRenderer(layer,fieldname,color_ramp, nb_classes, classif_method)
    ctx = QgsRenderContext()
    for symbol in renderer.symbols(ctx): # no border symbol
        symbol.symbolLayer(0).setStrokeStyle(0)
    
    setRenderer(layer,renderer)    
    
def setRendererUniqueValues(layer,fieldname):
    idx = layer.fields().indexOf(fieldname)
    # values = list(layer.uniqueValues(idx))
    values = [int(v) for v in list(layer.uniqueValues(idx))]
    values.sort()
    ranges = []
    for cpt, v in enumerate(values):
        lower = v - 0.5 if cpt == 0 else (v + values[cpt-1]) / 2
        upper = v + 0.5 if cpt == len(values) - 1 else (values[cpt+1] + v) / 2
        label = str(v)
        range = QgsRendererRange(lower,upper,QgsFillSymbol(),label)
        ranges.append(range)
    # print("ranges = " +str(ranges))
    renderer = QgsGraduatedSymbolRenderer (attrName=fieldname,ranges=ranges)
    color_ramp = getGradientColorRampRdYlGn(invert=False)
    renderer.updateColorRamp(color_ramp)
    setRenderer(layer,renderer)
     
# Raster utilities
    
def getValuesFromLayer3(layer):
    return qgsUtils.getRasterMinMedMax(layer)
    
def mkRasterShader(layer,color_ramp,classif_mode=QgsColorRampShader.Continuous):
    min, med, max = getValuesFromLayer3(layer)
    rasterShader = QgsRasterShader(minimumValue=min,maximumValue=max)
    colorRamp = getRandomSingleColorRamp()
    if not color_ramp:
        utils.internal_error("Could not create color ramp")        
    colorRampShader = QgsColorRampShader(minimumValue=min,maximumValue=max,
        colorRamp=color_ramp,classificationMode=classif_mode)
    colorRampShader.classifyColorRamp(band=1,input=layer.dataProvider())
    if colorRampShader.isEmpty():
        utils.internal_error("Empty color ramp shader")
    rasterShader.setRasterShaderFunction(colorRampShader)
    return rasterShader
    
def mkRandomColorRasterShader(layer):
    colorRamp = getRandomSingleColorRamp()
    return mkRasterShader(layer,colorRamp)
    
def mkQuantileShaderFromColorRamp(layer,colorRamp):
    return mkRasterShader(layer,colorRamp,classif_mode=QgsColorRampShader.Quantile)
    
# SBPC = Single Band Pseudo Color
def setSBPCRasterRenderer(layer,shader):
    if not shader:
        utils.internal_error("Could not create raster shader")
    renderer = QgsSingleBandPseudoColorRenderer(input=layer.dataProvider(),band=1,shader=shader)
    setRenderer(layer,renderer)
    
def setRandomColorRasterRenderer(layer):
    rasterShader = mkRandomColorRasterShader(layer)
    setSBPCRasterRenderer(layer,rasterShader)
    
# SBPC = Single Band Pseudo Color
def setRendererSBPCGnYlRd(layer):
    colorRamp = getGradientColorRampRdYlGn()
    shader = mkQuantileShaderFromColorRamp(layer,colorRamp)
    setSBPCRasterRenderer(layer,shader)
# SBPC = Single Band Pseudo Color - continuous
def setRendererSBPCGnYlRdCont(layer):
    colorRamp = getGradientColorRampRdYlGn()
    shader = mkRasterShader(layer,colorRamp)
    setSBPCRasterRenderer(layer,shader)
    
def mkRendererPalettedGnYlRd(layer):
    pr = layer.dataProvider()
    colorRamp = getGradientColorRampRdYlGn()
    classData = QgsPalettedRasterRenderer.classDataFromRaster(pr,1,ramp=colorRamp)
    renderer = QgsPalettedRasterRenderer(pr,1,classes=classData)
    return renderer
        
def setRendererPalettedGnYlRd(layer):
    renderer = mkRendererPalettedGnYlRd(layer)
    setRenderer(layer,renderer)

def setRendererPaletted(layer,colorRampStr,invert=False):
    colorRamp = mkColorRamp(colorRampStr,invert=invert)
    pr = layer.dataProvider()
    classData = QgsPalettedRasterRenderer.classDataFromRaster(pr,1,ramp=colorRamp)
    renderer = QgsPalettedRasterRenderer(pr,1,classes=classData)
    setRenderer(layer,renderer)
    
def setLightingQuantileStyle(layer):
    utils.info("setLightingQuantileStyle")
    colorRamp = mkColorRamp('Inferno')
    if not colorRamp:
        assert(False)
    shader = mkQuantileShaderFromColorRamp(layer,colorRamp)
    if not shader:
        assert(False)
    setSBPCRasterRenderer(layer,shader)
    
# def mkColorRampShaderPalettedGnYlRd(valueList,colorList):
    # lst =  []
    # for v, c in zip(valueList,colorList):
        # item = QgsColorRampShader.ColorRampItem(v,c)
        # lst.append(item)
    # colorRampShader = QgsColorRampShader()
    # colorRampShader.setColorRampItemList(lst)
    # return colorRampShader
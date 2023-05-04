# -*- coding: utf-8 -*-

"""
/***************************************************************************
ViewshedAnalysis
A QGIS plugin
begin : 2013-05-22
copyright : (C) 2013 by Zoran Čučković
email : /
***************************************************************************/

/***************************************************************************
* *
* This program is free software; you can redistribute it and/or modify *
* it under the terms of the GNU General Public License as published by *
* the Free Software Foundation version 2 of the License, or *
* any later version. *
* *
***************************************************************************/
"""

from os import path

from PyQt5.QtCore import QCoreApplication

from plugins.processing.gui import MessageBarProgress

from qgis.core import (QgsProcessing,
                       QgsProcessingMultiStepFeedback,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                       NULL,
                       QgsProcessingUtils,
                       #individual files
                       QgsProcessingOutputRasterLayer,

                       
                      QgsProcessingParameterBoolean,
                      QgsProcessingParameterNumber,
                      QgsProcessingParameterField,
                       QgsProcessingParameterEnum ,
                      QgsProcessingParameterFile,

                      QgsProcessingException,

                       QgsMessageLog)

from processing.core.ProcessingConfig import ProcessingConfig
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles


from .modules import visibility as ws
from .modules import Points as pts
from .modules import Raster as rst

import numpy as np
import time

class LightPointsViewshed(QgsProcessingAlgorithm):

    ALG_NAME = 'LightPointsViewshed'

    DEM = 'DEM'
    # OBSERVER_POINTS = 'OBSERVER_POINTS'
    LIGHT_PTS_INPUT = 'LumPointsExtraction'
    EXTENT_ZONE = 'ExtentZone'
    OBSERVER_HEIGHT = 'ObserverHeight'
    LIGHT_SOURCE_HEIGHT = 'LightHeight'
    LIGHT_SOURCE_HEIGHT_FIELD = 'LightHeightField'
    RADIUS_ANALYSIS = 'RadiusAnalysis'
    RADIUS_ANALYSIS_FIELD = 'RadiusAnalysisField'
    RASTER_BATI_INPUT = 'RasterBatiInput'
    
    OBSERVER_FIELD = 'observ_hgt' # old target_hgt
    SOURCE_FIELD = 'source_hgt' # old observ_hgt
    RADIUS_FIELD = 'radius'
    
    USE_CURVATURE = 'USE_CURVATURE'
    REFRACTION = 'REFRACTION'
    PRECISION = 'PRECISION'
    ANALYSIS_TYPE = 'ANALYSIS_TYPE'
    OPERATOR = 'OPERATOR'
    OUTPUT = 'OUTPUT'
   

    PRECISIONS = ['Coarse','Normal', 'Fine']

   
    TYPES = ['Binary viewshed', 'Depth below horizon','Horizon' ]
#              'Horizon - intermediate', 'Projected horizon']

  
    OPERATORS = [ 'Addition', "Minimum", "Maximum"]

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(self.LIGHT_PTS_INPUT, self.tr('Light points extraction'), [QgsProcessing.TypeVectorPoint], defaultValue=None))
        
        self.addParameter(QgsProcessingParameterField(self.LIGHT_SOURCE_HEIGHT_FIELD, self.tr('Source light height field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.LIGHT_SOURCE_HEIGHT, self.tr('Source light height (if no field), meters'), type=QgsProcessingParameterNumber.Double, defaultValue=6))
        
        self.addParameter(QgsProcessingParameterNumber(self.OBSERVER_HEIGHT, self.tr('Observer height (0, 1, 6, meters)'), type=QgsProcessingParameterNumber.Double, minValue=0, defaultValue=1))

        self.addParameter(QgsProcessingParameterField(self.RADIUS_ANALYSIS_FIELD, self.tr('Radius of analysis field for visibility'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.RADIUS_ANALYSIS, self.tr('Radius of analysis for visibility (if no field), meters'), type=QgsProcessingParameterNumber.Double, defaultValue=500))
        
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_BATI_INPUT, self.tr('Raster buildings vegetation')))
        
        # self.addParameter(
            # QgsProcessingParameterFeatureSource(
  
            # self.OBSERVER_POINTS,
            # self.tr('Sources location(s)'),
            # [QgsProcessing.TypeVectorPoint]))

        self.addParameter(QgsProcessingParameterRasterLayer
                          (self.DEM,
            self.tr('DES (Digital surface model)')))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_CURVATURE,
            self.tr('Take in account Earth curvature'),
            False))

        param = QgsProcessingParameterEnum(
            self.ANALYSIS_TYPE,
            self.tr('Analysis type'),
            self.TYPES, defaultValue=0)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)     
        
        param = QgsProcessingParameterNumber(
            self.REFRACTION,
            self.tr('Atmoshpheric refraction'),
            1, 0.13, False, 0.0, 1.0)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        
##        self.addParameter(QgsProcessingParameterEnum (
##            self.PRECISION,
##            self.tr('Algorithm precision'),
##            self.PRECISIONS,
##            defaultValue=1))
        
        param = QgsProcessingParameterEnum (
            self.OPERATOR,
            self.tr('Combining multiple outputs'),
            self.OPERATORS,
            defaultValue=0)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
            self.tr("Output file")))

    # def shortHelpString(self):
        
        # curr_dir = path.dirname(path.realpath(__file__))
        # h = (f"""
            # Produces a visibility map where each observer point on a terrain model. The output can be:
            # <ul>
                # <li> Binary viewshed: visible/not visible (1/0).</li>
                # <li> Depth below horizon: height that each location should attain in order to become visible.</li>
                # <li> Horizon: outer edges of a viewshed. </li>
            # </ul>

            # Terrain model used should be in the same projection system as viewpoints file (preferably the one used in "Create viewpoints" routine).
            
            # When multiple observer points are used, individual viewsheds will be combined according to the Combinig multiple ouptuts option.
          
            # <h3>Parameters</h3>

            # <ul>
                # <li> <em>Observer locations</em>: viewpoints created by the "Create viewpoints" routine.</li>
                # <li> <em>Digital elevation model</em>: DEM in the same projection system as viewpoints file.</li>
            # </ul>

            # For more see <a href="http://zoran-cuckovic.github.io/QGIS-visibility-analysis/help_qgis3.html">help online</a>.
            
            # If you find this tool useful, consider to :
                 
             # <a href='https://ko-fi.com/D1D41HYSW' target='_blank'><img height='30' style='border:0px;height:36px;' src='{curr_dir}/kofi2.webp' /></a>
            
			# This GIS tool is intended for peaceful use !
			# <img height='80' style='border:0px;height:36px;' src='{curr_dir}/ukraine.png'/>
			
			# """) 

        # return h            

    # #---------- not working ---------------- 
    # def helpUrl(self):
        # return 'https://zoran-cuckovic.github.io/QGIS-visibility-analysis/help_qgis3.html'
    # # for local file : QUrl.fromLocalFile(os.path.join(helpPath, '{}.html'.format(self.grass7Name))).toString()
        
    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1] 
        self.inputLightPoints = qgsTreatments.parameterAsSourceLayer(self, parameters,self.LIGHT_PTS_INPUT,context,feedback=feedback)[1] 
        
        self.inputRasterBatiVege = self.parameterAsRasterLayer(parameters, self.RASTER_BATI_INPUT, context)
        
        self.raster = self.parameterAsRasterLayer(parameters,self.DEM, context)
        self.useEarthCurvature = self.parameterAsBool(parameters,self.USE_CURVATURE,context)
        self.refraction = self.parameterAsDouble(parameters,self.REFRACTION,context)
        self.precision = 1#self.parameterAsInt(parameters,self.PRECISION,context)
        self.analysis_type = self.parameterAsInt(parameters,self.ANALYSIS_TYPE, context)
        self.operator = self.parameterAsInt(parameters,self.OPERATOR,context) +1       

        self.output_path = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
    def processAlgorithm(self, parameters, context, feedback):

        self.parseParams(parameters,context, feedback)
        outputs = {}
        # observers = self.parameterAsSource(parameters,self.OBSERVER_POINTS,context)
# --------------- get observers (light points) ------------------       
        feedback = QgsProcessingMultiStepFeedback(100, feedback)
        feedback.setCurrentStep(0)
        # Extraire l'emprise de la couche
        # Si emprise non présente, on prend celle des points lumineux
        print(self.inputLightPoints)
        if self.inputExtent is None or self.inputExtent == NULL:
            extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
            outputs[self.EXTENT_ZONE] = qgsTreatments.applyGetLayerExtent(self.inputLightPoints, extent_zone, context=context,feedback=feedback)
            
        else:
            # Tampon
            expr = parameters[self.RADIUS_ANALYSIS]
            temp_path_buf = QgsProcessingUtils.generateTempFilename('temp_path_buf.gpkg')
            qgsTreatments.applyBufferFromExpr(self.inputExtent,expr, temp_path_buf,context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] =  qgsUtils.loadVectorLayer(temp_path_buf)
            
                
        # Extraire par localisation
        temp_path_pts = QgsProcessingUtils.generateTempFilename('temp_path_pts.gpkg')
        qgsTreatments.extractByLoc(self.inputLightPoints, outputs[self.EXTENT_ZONE],temp_path_pts, context=context,feedback=feedback)
        outputs['LocalisationPointsExtraction'] = qgsUtils.loadVectorLayer(temp_path_pts)
        

        # Ajouter un champ auto-incrémenté
        temp_path_auto_incr = QgsProcessingUtils.generateTempFilename('temp_path_auto_incr.gpkg')
        qgsTreatments.applyAutoIncrementField(outputs['LocalisationPointsExtraction'], 'ID', temp_path_auto_incr, context=context,feedback=feedback)
        outputs['AddFieldIncr'] = qgsUtils.loadVectorLayer(temp_path_auto_incr)
        

        # Calculatrice de champ observateur (target)
        formula = parameters[self.OBSERVER_HEIGHT]

        temp_path_obs = QgsProcessingUtils.generateTempFilename('temp_path_obs.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['AddFieldIncr'], self.OBSERVER_FIELD, temp_path_obs, formula, 10, 4, 0, context=context,feedback=feedback)
        outputs['CalculFieldObserv'] = qgsUtils.loadVectorLayer(temp_path_obs)
        

        # Calculatrice de champ radius
        if parameters[self.RADIUS_ANALYSIS_FIELD] != "" and parameters[self.RADIUS_ANALYSIS_FIELD] is not None and parameters[self.RADIUS_ANALYSIS_FIELD] != NULL:
            formula = '"'+parameters[self.RADIUS_ANALYSIS_FIELD]+'"'
        else:
            formula = parameters[self.RADIUS_ANALYSIS]
        
        temp_path_radius = QgsProcessingUtils.generateTempFilename('temp_path_radius.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['CalculFieldObserv'],self.RADIUS_FIELD,temp_path_radius, formula, 10, 4, 0, context=context,feedback=feedback)
        outputs['CalculFieldRadius'] = qgsUtils.loadVectorLayer(temp_path_radius)
        
        # Mise à 0 nécessaire de la hauteur de la source si interescte le bati ou la végétation
        
        # Raster vers vecteur du raster bati vegetation
        outputs['PolygoniseBatiVege'] = qgsTreatments.applyPolygonize(self.inputRasterBatiVege, 'DN', QgsProcessing.TEMPORARY_OUTPUT, context=context, feedback=feedback)
        
        # Jointure par localisation entre les points et bati-végétation
        temp_path_join_pts_bati = QgsProcessingUtils.generateTempFilename('temp_path_join_pts_bati.gpkg')
        qgsTreatments.joinByLoc(outputs['CalculFieldRadius'],outputs['PolygoniseBatiVege'],predicates=[0],out_path=temp_path_join_pts_bati,discard=False,method=1,context=context,feedback=feedback)
        outputs['JoinPointsBatiVege'] = qgsUtils.loadVectorLayer(temp_path_join_pts_bati)
        
        # Calculatrice de champ hauteur source lumière (si intersection : DN non NULL, on met la hauteur à 0
        if parameters[self.LIGHT_SOURCE_HEIGHT_FIELD] != "" and parameters[self.LIGHT_SOURCE_HEIGHT_FIELD] is not None and parameters[self.LIGHT_SOURCE_HEIGHT_FIELD] != NULL:
            formula = 'CASE WHEN  "DN" IS NULL THEN "'+str(parameters[self.LIGHT_SOURCE_HEIGHT_FIELD])+'" ELSE 0 END'
        else:
            formula = 'CASE WHEN  "DN" IS NULL THEN '+str(parameters[self.LIGHT_SOURCE_HEIGHT])+' ELSE 0 END'
        
        temp_path_lum_pts = QgsProcessingUtils.generateTempFilename('temp_path_lum_pts.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['JoinPointsBatiVege'],self.SOURCE_FIELD, temp_path_lum_pts, formula, 10, 4, 0, context=context,feedback=feedback)
        outputs['LightPoints'] = qgsUtils.loadVectorLayer(temp_path_lum_pts)
        
# --------------- verification of inputs ------------------

        raster_path= self.raster.source()
        dem = rst.Raster(raster_path, output=self.output_path)
        


        # Get result of first points extractions
        points = pts.Points(outputs['LightPoints']) #pts.Points(observers)
        miss = points.test_fields(["source_hgt", "radius"])
           
        
        if miss:
            err= " \n ****** \n ERROR! \n Missing fields: \n" + "\n".join(miss)
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err)

        miss_params = points.test_fields(["radius_in", "azim_1", "azim_2"])
        
        points.take(dem.extent, dem.pix)

        if points.count == 0:
            err= "  \n ******* \n ERROR! \n No viewpoints in the chosen area!"
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err )

        elif points.count == 1:
            operator=0
            live_memory = False

        else:
            if (ProcessingConfig.getSetting('MEMORY_BUFFER_SIZE')) is None:
                operator=0
                live_memory = False
            else:
                live_memory = ( (dem.size[0] * dem.size[1]) / 1000000 <
                               float(ProcessingConfig.getSetting(
                                   'MEMORY_BUFFER_SIZE')))
        
        dem.set_buffer(self.operator, live_memory = live_memory)
            
        # prepare the output raster
        if not live_memory:
            # !! we cannot use compression because of a strange memory bloat 
            # produced by GDAL
            dem.write_output(self.output_path, compression = False)

        pt = points.pt #this is a dict of obs. points
# --------------------- analysis ----------------------   

        start = time.process_time()
        report = []

        
        #for speed and convenience, use maximum sized window for all analyses
        
        dem.set_master_window(points.max_radius,
                            size_factor = self.precision ,
                            background_value=0,
                            pad = self.precision>0,
                            curvature =self.useEarthCurvature,
                            refraction = self.refraction )
        


        cnt = 0
       
        for id1 in pt :     

            if feedback.isCanceled():  break
          

            matrix_vis = ws.viewshed_raster (self.analysis_type, pt[id1], dem,
                                          interpolate = self.precision > 0)

            # must set the mask before writing the result!
            mask = [pt[id1]["radius"]]

            inner_radius_specified = "radius_in" not in miss_params
            if inner_radius_specified:
                mask += [ pt[id1]["radius_in"] ]

            if  "azim_1" not in miss_params and  "azim_2" not in miss_params:
                if not inner_radius_specified:
                    mask += [ None ]
                mask += [ pt[id1]["azim_1"], pt[id1]["azim_2"] ]
                print (mask)

            dem.set_mask(*mask)

            r = dem.add_to_buffer (matrix_vis, report = True)
            
            
            report.append([pt[id1]["id"],*r])

            cnt += 1

            feedback.setCurrentStep(int((cnt/points.count) *100))
            # feedback.setProgress(int((cnt/points.count) *100))
            if feedback.isCanceled(): return {}
                
       
        if live_memory: dem.write_output(self.output_path)
        
        dem = None

        txt = ("\n Analysis time: " + str(
            round((time.process_time() - start
                                    ) / 60, 2)) + " minutes."
              " \n.      RESULTS \n Point_ID, visible pixels, total pixels" )
        
        for l in report:
            txt = txt + "\n" + ' , '.join(str(x) for x in l)

        # TODO : write to Results viewer !!
        QgsMessageLog.logMessage( txt, "Viewshed info")
          
        results = {}
        
        results[self.OUTPUT] = self.output_path
        # for output in self.outputDefinitions():
            # outputName = output.name()
                
            # if outputName in parameters :
                # results[outputName] = parameters[outputName]

    
        return results

    
    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """

        return 'LightPointsViewshed'
    
    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Calcul of Viewshed')
    
    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Visibility Light Sources')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'VisibilityLightSources'

    def tr(self, string):
        return QCoreApplication.translate(self.__class__.__name__, string)

    def createInstance(self):
        #return ViewshedPoints() NORMALLY
        # return type(self)()
        return LightPointsViewshed()

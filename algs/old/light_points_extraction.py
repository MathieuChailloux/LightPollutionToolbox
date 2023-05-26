"""
Model exported as python.
Name : Extraction_points_lum
Group : Visibility Light Sources
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingUtils
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterRasterLayer
from qgis import processing
from ...qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles


class LightPointsExtraction(QgsProcessingAlgorithm):
    
    ALG_NAME = 'LightPointsExtraction'
    
    LIGHT_PTS_INPUT = 'LumPointsExtraction'
    EXTENT_ZONE = 'ExtentZone'
    OBSERVER_HEIGHT = 'ObserverHeight'
    # OBSERVER_HEIGHT_FIELD = 'ObserverHeightField'
    LIGHT_SOURCE_HEIGHT = 'LightHeight'
    LIGHT_SOURCE_HEIGHT_FIELD = 'LightHeightField'
    RADIUS_ANALYSIS = 'RadiusAnalysis'
    RADIUS_ANALYSIS_FIELD = 'RadiusAnalysisField'
    RASTER_BATI_INPUT = 'RasterBatiInput'

    OUTPUT_LUM_PTS = 'OutputLightPoints'
    
    OBSERVER_FIELD = 'observ_hgt' # old target_hgt
    SOURCE_FIELD = 'source_hgt' # old observ_hgt
    RADIUS_FIELD = 'radius'
    
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(self.LIGHT_PTS_INPUT, self.tr('Light points extraction'), [QgsProcessing.TypeVectorPoint], defaultValue=None))
        
        self.addParameter(QgsProcessingParameterField(self.LIGHT_SOURCE_HEIGHT_FIELD, self.tr('Source light height field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.LIGHT_SOURCE_HEIGHT, 'Source light height (if no field), meters', type=QgsProcessingParameterNumber.Double, defaultValue=6))

        # self.addParameter(QgsProcessingParameterField(self.OBSERVER_HEIGHT_FIELD, self.tr('Observer height field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.OBSERVER_HEIGHT, 'Observer height (if no field) 0, 1, 6, meters', type=QgsProcessingParameterNumber.Double, minValue=0, defaultValue=1))

        self.addParameter(QgsProcessingParameterField(self.RADIUS_ANALYSIS_FIELD, self.tr('Radius of analysis field for visibility'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.RADIUS_ANALYSIS, 'Radius of analysis for visibility (if no field), meters', type=QgsProcessingParameterNumber.Double, defaultValue=500))
        
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_BATI_INPUT, self.tr('Raster buildings vegetation')))
        
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_LUM_PTS, self.tr('Light points extraction for ViewShed'), type=QgsProcessing.TypeVectorAnyGeometry))

    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1] 
        self.inputLightPoints = qgsTreatments.parameterAsSourceLayer(self, parameters,self.LIGHT_PTS_INPUT,context,feedback=feedback)[1] 
        self.inputRasterBatiVege = self.parameterAsRasterLayer(parameters, self.RASTER_BATI_INPUT, context)

        self.outputLightPts = self.parameterAsOutputLayer(parameters,self.OUTPUT_LUM_PTS, context)
        
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(8, model_feedback)
        
        outputs = {}
        
        self.parseParams(parameters, context, feedback)

        # Extraire l'emprise de la couche
        # Si emprise non présente, on prend celle des points lumineux
        if self.inputExtent is None or self.inputExtent == NULL:
            extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
            outputs[self.EXTENT_ZONE] = qgsTreatments.applyGetLayerExtent(self.inputLightPoints, extent_zone, context=context,feedback=feedback)
            
        else:
            # Tampon
            expr = parameters[self.RADIUS_ANALYSIS]
            temp_path_buf = QgsProcessingUtils.generateTempFilename('temp_path_buf.gpkg')
            qgsTreatments.applyBufferFromExpr(self.inputExtent,expr, temp_path_buf,context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] =  qgsUtils.loadVectorLayer(temp_path_buf)
            
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}
                
        # Extraire par localisation
        temp_path_pts = QgsProcessingUtils.generateTempFilename('temp_path_pts.gpkg')
        qgsTreatments.extractByLoc(self.inputLightPoints, outputs[self.EXTENT_ZONE],temp_path_pts, context=context,feedback=feedback)
        outputs['LocalisationPointsExtraction'] = qgsUtils.loadVectorLayer(temp_path_pts)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Ajouter un champ auto-incrémenté
        temp_path_auto_incr = QgsProcessingUtils.generateTempFilename('temp_path_auto_incr.gpkg')
        qgsTreatments.applyAutoIncrementField(outputs['LocalisationPointsExtraction'], 'ID', temp_path_auto_incr, context=context,feedback=feedback)
        outputs['AddFieldIncr'] = qgsUtils.loadVectorLayer(temp_path_auto_incr)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ observateur (target)
        formula = parameters[self.OBSERVER_HEIGHT]

        temp_path_obs = QgsProcessingUtils.generateTempFilename('temp_path_obs.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['AddFieldIncr'], self.OBSERVER_FIELD, temp_path_obs, formula, 10, 4, 0, context=context,feedback=feedback)
        outputs['CalculFieldObserv'] = qgsUtils.loadVectorLayer(temp_path_obs)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ radius
        if parameters[self.RADIUS_ANALYSIS_FIELD] is not None and parameters[self.RADIUS_ANALYSIS_FIELD] != NULL:
            formula = '"'+parameters[self.RADIUS_ANALYSIS_FIELD]+'"'
        else:
            formula = parameters[self.RADIUS_ANALYSIS]
        
        temp_path_radius = QgsProcessingUtils.generateTempFilename('temp_path_radius.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['CalculFieldObserv'],self.RADIUS_FIELD,temp_path_radius, formula, 10, 4, 0, context=context,feedback=feedback)
        outputs['CalculFieldRadius'] = qgsUtils.loadVectorLayer(temp_path_radius)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Mise à 0 nécessaire de la hauteur de la source si interescte le bati ou la végétation
        
        # Raster vers vecteur du raster bati vegetation
        outputs['PolygoniseBatiVege'] = qgsTreatments.applyPolygonize(self.inputRasterBatiVege, 'DN', QgsProcessing.TEMPORARY_OUTPUT, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Jointure par localisation entre les points et bati-végétation
        temp_path_join_pts_bati = QgsProcessingUtils.generateTempFilename('temp_path_join_pts_bati.gpkg')
        qgsTreatments.joinByLoc(outputs['CalculFieldRadius'],outputs['PolygoniseBatiVege'],predicates=[0],out_path=temp_path_join_pts_bati,discard=False,method=1,context=context,feedback=feedback)
        outputs['JoinPointsBatiVege'] = qgsUtils.loadVectorLayer(temp_path_join_pts_bati)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Calculatrice de champ hauteur source lumière (si intersection : DN non NULL, on met la hauteur à 0
        if parameters[self.LIGHT_SOURCE_HEIGHT_FIELD] != "" and parameters[self.LIGHT_SOURCE_HEIGHT_FIELD] is not None and parameters[self.LIGHT_SOURCE_HEIGHT_FIELD] != NULL:
            formula = 'CASE WHEN  "DN" IS NULL THEN "'+str(parameters[self.LIGHT_SOURCE_HEIGHT_FIELD])+'" ELSE 0 END'
        else:
            formula = 'CASE WHEN  "DN" IS NULL THEN '+str(parameters[self.LIGHT_SOURCE_HEIGHT])+' ELSE 0 END'
        
        self.results[self.OUTPUT_LUM_PTS] = qgsTreatments.applyFieldCalculator(outputs['JoinPointsBatiVege'],self.SOURCE_FIELD,self.outputLightPts, formula, 10, 4, 0, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        print(step)
        
        return self.results

    def name(self):
        return 'LightPointsExtraction'

    def displayName(self):
        return self.tr('Light points extraction')

    def group(self):
        return  self.tr('Light Pollution Indicators')

    def groupId(self):
        return 'lightPollutionIndicators'
        
    def tr(self, string):
        return QCoreApplication.translate(self.__class__.__name__, string)

    def createInstance(self):
        return LightPointsExtraction()

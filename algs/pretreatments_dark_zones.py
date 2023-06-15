"""
Model exported as python.
Name : Prétraitement d'image raster pour enlever les zones sombres
Group : POLLUM
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingUtils
from qgis.core import Qgis
from qgis.core import QgsProject
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles

# TODO : ajouter prétraitements pour enlever les pixels mono-couleurs ?
class PretreatmentsDarkZones(QgsProcessingAlgorithm):
    
    RASTER_INPUT = 'ImageSat'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    EXTENT_ZONE = 'ExtentZone'
    SLICED_RASTER = 'SlicedRaster'

    OUTPUT_RASTER = 'OutputRaster'
    
    MAJORITY_FIELD = "_majority"

    results = {}
    
    def initAlgorithm(self, config=None):
    
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))

        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Satellite Image RGB'),defaultValue=None))

        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER, self.tr('Clean Raster'), defaultValue=None))
        
        param = QgsProcessingParameterNumber(self.RED_BAND_INPUT, self.tr('Index of the red band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=1)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.GREEN_BAND_INPUT, self.tr('Index of the green band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=2)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.BLUE_BAND_INPUT, self.tr('Index of the blue band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=3)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1]  
        self.inputRaster = self.parameterAsRasterLayer(parameters, self.RASTER_INPUT, context)
        self.outputRaster = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER,context)
    
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
        outputs = {}
        
        self.parseParams(parameters, context, feedback)

        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Extraire l'emprise de la couche raster
            extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
            outputs[self.EXTENT_ZONE] =  qgsTreatments.applyGetLayerExtent(self.inputRaster, extent_zone, context=context,feedback=feedback)
            outputs[self.SLICED_RASTER] = self.inputRaster # le raster n'est pas découpé
            
        else:
            # Découper un raster selon une emprise
            outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] = self.inputExtent
            
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Statistiques de zone pour les 3 bandes afin de récupérer les pixels majoritaires
        majorityBand1 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        majorityBand2 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.GREEN_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        majorityBand3 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.BLUE_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Calculatrice Raster masque pour enlever les zones non éclairées
        # Si les pixels < majortité+1 alors 0, sinon 1 
        # Ici la condition indique l'inverse : pour mettre les pixels à 1, il faut qu'au moins 1 des 3 soit > majorité
        # Pour enlver le bruit qui correspond à des couleurs uniques ou seule une bande a une valeur forte, on vérifie qu'au moins 2 bandes aient une valeur > majortité
        # #(A > maj1 AND B > maj2) OR (A > maj1 AND C > maj3) OR (B > maj2 AND C > maj3)
        # 'FORMULA': '1*logical_or(logical_or(logical_and((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')),logical_and((A>'+str(majorityBand1)+'), (C>'+str(majorityBand3)+'))),logical_and((B>'+str(majorityBand2)+'), (C>'+str(majorityBand3)+')))',

        formula = '1*logical_or(logical_or((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')), (C >'+str(majorityBand3)+'))'
        outputs['CalculRasterMask'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],parameters[self.GREEN_BAND_INPUT], parameters[self.BLUE_BAND_INPUT],QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Calculatrice Raster B1 avec masque
        formula = 'A*B'
        outputs['CalculRasterB1'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.RED_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Calculatrice Raster B2 avec masque
        formula = 'A*B'
        outputs['CalculRasterB2'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.GREEN_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Calculatrice Raster B3 avec masque
        formula = 'A*B'
        outputs['CalculRasterB3'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.BLUE_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}        
        
        # Fusion
        outputs['Merge'] = qgsTreatments.applyMergeRaster([outputs['CalculRasterB1'],outputs['CalculRasterB2'],outputs['CalculRasterB3']],self.outputRaster,out_type=Qgis.UInt16, context=context,feedback=feedback)
        self.results['Raster'] = outputs['Merge']
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}  
        
        print(step)
        return self.results

    def name(self):
        return 'PretreatmentsDarkZones'

    def displayName(self):
        return self.tr('Pretreatments to remove dark zones')
        
    def group(self):
        return self.tr('Utils Light Pollution Indicators')

    def groupId(self):
        return 'utilsLightPollutionIndicators'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate(self.__class__.__name__, string)
        
    def createInstance(self):
        return PretreatmentsDarkZones()

    # def postProcessAlgorithm(self,context,feedback):
        # QgsProject.instance().addMapLayer(self, addToLegend=True)
        # print('postProcessAlgorithm')
        # return self.results
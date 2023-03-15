"""
Model exported as python.
Name : Prétraitement d'image reaster pour enlever les zones sombres
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
from qgis.core import QgsProcessingUtils
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles

# TODO : ajouter prétraitements pour enlever les pixels mono-couleurs ?
class PretreatmentsDarkZones(QgsProcessingAlgorithm):
    
    RASTER_INPUT = 'ImageJILINradianceRGB'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    EXTENT_ZONE = 'ExtentZone'
    SLICED_RASTER = 'SlicedRaster'

    OUTPUT_RASTER = 'OutputRaster'
    
    MAJORITY_FIELD = "_majority"

        
    def initAlgorithm(self, config=None):
    
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))

        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Image JILIN radiance RGB'),defaultValue=None))

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

    def parseParams(self, parameters, context):
        self.inputExtent = self.parameterAsVectorLayer(parameters, self.EXTENT_ZONE, context)
        self.inputRaster = self.parameterAsRasterLayer(parameters, self.RASTER_INPUT, context)
        self.outputRaster = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER,context)
    
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        results = {}
        outputs = {}
        
        self.parseParams(parameters,context)

        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Extraire l'emprise de la couche raster
            extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
            alg_params = {
                'INPUT': self.inputRaster,
                'ROUND_TO': 0,
                'OUTPUT': extent_zone #QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
                    
            outputs[self.SLICED_RASTER] = self.inputRaster # le raster n'est pas découpé
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        else:
            # Découper un raster selon une emprise
            alg_params = {
                'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                'EXTRA': '',
                'INPUT': self.inputRaster,
                'NODATA': None,
                'OPTIONS': '',
                'OVERCRS': False,
                'PROJWIN': self.inputExtent,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.SLICED_RASTER] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            outputs[self.EXTENT_ZONE] = self.inputExtent

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
            
        # Statistiques de zone pour les 3 bandes afin de récupérer les pixels majoritaires
        majorityBand1 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        majorityBand2 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.GREEN_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        majorityBand3 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.BLUE_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)

        # Calculatrice Raster masque pour enlever les zones non éclairées
        # Si les pixels < majortité+1 alors 0, sinon 1 
        # Ici la condition indique l'inverse : pour mettre les pixels à 1, il faut qu'au moins 1 des 3 soit > majorité
        # Pour enlver le bruit qui correspond à des couleurs uniques ou seule une bande a une valeur forte, on vérifie qu'au moins 2 bandes aient une valeur > majortité
        # #(A > maj1 AND B > maj2) OR (A > maj1 AND C > maj3) OR (B > maj2 AND C > maj3)
        # 'FORMULA': '1*logical_or(logical_or(logical_and((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')),logical_and((A>'+str(majorityBand1)+'), (C>'+str(majorityBand3)+'))),logical_and((B>'+str(majorityBand2)+'), (C>'+str(majorityBand3)+')))',
        alg_params = {
            'BAND_A': parameters[self.RED_BAND_INPUT], #1
            'BAND_B': parameters[self.GREEN_BAND_INPUT], #2
            'BAND_C': parameters[self.BLUE_BAND_INPUT], #3
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': '1*logical_or(logical_or((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')), (C >'+str(majorityBand3)+'))',
            'INPUT_A': outputs[self.SLICED_RASTER],
            'INPUT_B': outputs[self.SLICED_RASTER],
            'INPUT_C': outputs[self.SLICED_RASTER],
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 1,  # Int16
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculRasterMask'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
        
        # Calculatrice Raster B1 avec masque
        alg_params = {
            'BAND_A': parameters[self.RED_BAND_INPUT],
            'BAND_B': 1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*B',
            'INPUT_A': outputs[self.SLICED_RASTER],
            'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculRasterB1'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
            
        # Calculatrice Raster B2 avec masque
        alg_params = {
            'BAND_A': parameters[self.GREEN_BAND_INPUT],
            'BAND_B': 1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*B',
            'INPUT_A': outputs[self.SLICED_RASTER],
            'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculRasterB2'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
            
        # Calculatrice Raster B3 avec masque
        alg_params = {
            'BAND_A': parameters[self.BLUE_BAND_INPUT],
            'BAND_B': 1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*B',
            'INPUT_A': outputs[self.SLICED_RASTER],
            'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculRasterB3'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}        
        
        # Fusion
        alg_params = {
            'DATA_TYPE': 5,  # Float32
            'EXTRA': '',
            'INPUT': [outputs['CalculRasterB1']['OUTPUT'],outputs['CalculRasterB2']['OUTPUT'],outputs['CalculRasterB3']['OUTPUT']],
            'NODATA_INPUT': None,
            'NODATA_OUTPUT': None,
            'OPTIONS': '',
            'PCT': False,
            'SEPARATE': True,
            'OUTPUT': self.outputRaster
        }
        outputs['Merge'] = processing.run('gdal:merge', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Raster'] = outputs['Merge']['OUTPUT']
        
        print(step)
        return results

    def name(self):
        return self.tr('Pretreatments to remove dark zones')

    def displayName(self):
        return self.tr('Pretreatments to remove dark zones')
        
    def group(self):
        return 'ASE'

    def groupId(self):
        return 'ASE'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)
        
    def createInstance(self):
        return PretreatmentsDarkZones()

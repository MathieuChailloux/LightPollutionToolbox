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
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles


class LightPointsExtraction(QgsProcessingAlgorithm):
    
    ALG_NAME = 'LightPointsExtraction'
    
    LIGHT_PTS_INPUT = 'LumPointsExtraction'
    EXTENT_ZONE = 'ExtentZone'
    OBSERVER_HEIGHT = 'ObserverHeight'
    OBSERVER_HEIGHT_FIELD = 'ObserverHeightField'
    LIGHT_HEIGHT = 'LightHeight'
    LIGHT_HEIGHT_FIELD = 'LightHeightField'
    RADIUS_ANALYSIS = 'RadiusAnalysis'
    RADIUS_ANALYSIS_FIELD = 'RadiusAnalysisField'
    OUTPUT_LUM_PTS = 'OutputLightPoints'
    
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer(self.LIGHT_PTS_INPUT, self.tr('Light points extraction'), types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        
        self.addParameter(QgsProcessingParameterField(self.OBSERVER_HEIGHT_FIELD, self.tr('Observer height field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.OBSERVER_HEIGHT, 'Observer height (if no field) 0, 1, 6, meters', type=QgsProcessingParameterNumber.Double, minValue=0, defaultValue=1))

        self.addParameter(QgsProcessingParameterField(self.LIGHT_HEIGHT_FIELD, self.tr('Source light height field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.LIGHT_HEIGHT, 'Source light height (if no field), meters', type=QgsProcessingParameterNumber.Double, defaultValue=6))

        self.addParameter(QgsProcessingParameterField(self.RADIUS_ANALYSIS_FIELD, self.tr('Radius of analysis field for visibility'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.LIGHT_PTS_INPUT, allowMultiple=False,defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.RADIUS_ANALYSIS, 'Radius of analysis for visibility (if no field), meters', type=QgsProcessingParameterNumber.Double, defaultValue=500))

        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_LUM_PTS, self.tr('Light points extraction for ViewShed'), type=QgsProcessing.TypeVectorAnyGeometry))

    def parseParams(self, parameters, context):
        self.inputExtent = self.parameterAsVectorLayer(parameters, self.EXTENT_ZONE, context)
        self.inputLightPoints = self.parameterAsVectorLayer(parameters, self.LIGHT_PTS_INPUT, context)
        self.outputLightPts = self.parameterAsOutputLayer(parameters,self.OUTPUT_LUM_PTS, context)
        
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        
        outputs = {}
        
        self.parseParams(parameters,context)

        # Extraire l'emprise de la couche
        # Si emprise non présente, on prend celle des points lumineux
        if self.inputExtent is None or self.inputExtent == NULL:
            alg_params = {
                'INPUT': self.inputLightPoints,
                'ROUND_TO': 0,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
        else:
            # Tampon
            alg_params = {
                'DISSOLVE': False,
                'DISTANCE': parameters[self.RADIUS_ANALYSIS],
                'END_CAP_STYLE': 0,  # Rond
                'INPUT': self.inputExtent,
                'JOIN_STYLE': 0,  # Rond
                'MITER_LIMIT': 2,
                'SEGMENTS': 5,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.EXTENT_ZONE] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}
                
        # Extraire par localisation
        alg_params = {
            'INPUT': self.inputLightPoints,
            'INTERSECT': outputs[self.EXTENT_ZONE],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LocalisationPointsExtraction'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Ajouter un champ auto-incrémenté
        alg_params = {
            'FIELD_NAME': 'ID',
            'GROUP_FIELDS': [''],
            'INPUT': outputs['LocalisationPointsExtraction']['OUTPUT'],
            'MODULUS': 0,
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': '',
            'SORT_NULLS_FIRST': False,
            'START': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddFieldIncr'] = processing.run('native:addautoincrementalfield', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ observateur (target)
        if parameters[self.OBSERVER_HEIGHT_FIELD] is not None and parameters[self.OBSERVER_HEIGHT_FIELD] != NULL:
            formula = '"'+parameters[self.OBSERVER_HEIGHT_FIELD]+'"'
        else:
            formula = parameters[self.OBSERVER_HEIGHT]
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'observ_hgt', # old target_hgt
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': formula,
            'INPUT': outputs['AddFieldIncr']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldObserv'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ radius
        if parameters[self.RADIUS_ANALYSIS_FIELD] is not None and parameters[self.RADIUS_ANALYSIS_FIELD] != NULL:
            formula = '"'+parameters[self.RADIUS_ANALYSIS_FIELD]+'"'
        else:
            formula = parameters[self.RADIUS_ANALYSIS]
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'radius',
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': formula,
            'INPUT': outputs['CalculFieldObserv']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldRadius'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ hauteur source lumière
        if parameters[self.LIGHT_HEIGHT_FIELD] is not None and parameters[self.LIGHT_HEIGHT_FIELD] != NULL:
            formula = '"'+parameters[self.LIGHT_HEIGHT_FIELD]+'"'
        else:
            formula = parameters[self.LIGHT_HEIGHT]
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'source_hgt', # old observ_hgt
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': formula,
            'INPUT': outputs['CalculFieldRadius']['OUTPUT'],
            'OUTPUT': self.outputLightPts
        }
        outputs['CalculFieldLightHgt'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        self.results[self.OUTPUT_LUM_PTS] = outputs['CalculFieldLightHgt']['OUTPUT']

        print(step)
        
        return self.results

    def name(self):
        return 'LightPointsExtraction'

    def displayName(self):
        return self.tr('Light points extraction')

    def group(self):
        return  self.tr('Visibility Light Sources')

    def groupId(self):
        return  self.tr('Visibility Light Sources')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return LightPointsExtraction()

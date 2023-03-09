"""
Model exported as python.
Name : MNB
Group : Visibility Light Sources
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingUtils
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterField
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles


class CalculMnb(QgsProcessingAlgorithm):

    ALG_NAME = 'CalculMnb'
    
    RASTER_MNT_INPUT = 'MNT'
    BATI_INPUT = 'BatiBDTopo'
    EXTENT_ZONE = 'ExtentZone'
    HEIGHT_FIELD_BATI = 'HeightFieldBati'
    SLICED_RASTER = 'SlicedRaster'
    OUTPUT_RASTER_MNB = 'OutputMNB'
    OUTPUT_RASTER_BATI = 'RasterBati'
    
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_MNT_INPUT, self.tr('MNT'), defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer(self.BATI_INPUT, self.tr('Buildings (BD TOPO)'), types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterField(self.HEIGHT_FIELD_BATI, self.tr('Height Buildings fields'), type=QgsProcessingParameterField.Any, parentLayerParameterName=self.BATI_INPUT, allowMultiple=False, defaultValue='HAUTEUR'))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_MNB, self.tr('MNB'), createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_BATI, self.tr('Raster bati'), createByDefault=True, defaultValue=None))

    def parseParams(self, parameters, context):
        self.inputExtent = self.parameterAsVectorLayer(parameters, self.EXTENT_ZONE, context)
        self.inputRasterMNT = self.parameterAsRasterLayer(parameters, self.RASTER_MNT_INPUT, context)
        self.inputBati= self.parameterAsVectorLayer(parameters, self.BATI_INPUT, context)
        self.outputRasterMNB = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_MNB,context)
        self.outputRasterBati = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_BATI,context)
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(8, model_feedback)
       
        outputs = {}
        
        self.parseParams(parameters,context)
        
        # Extraire l'emprise de la couche
        # Si emprise non présente, on prend celle du MNB
        if self.inputExtent is None or self.inputExtent == NULL:
            alg_params = {
                    'INPUT': self.inputRasterMNT,
                    'ROUND_TO': 0,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
            outputs[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            outputs[self.SLICED_RASTER] = self.inputRasterMNT # le raster n'est pas découpé
            
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        else:
            # Tampon
            alg_params = {
                'DISSOLVE': False,
                'DISTANCE': 500, # TODO : récupérer la valeur de Light Points Extraction
                'END_CAP_STYLE': 0,  # Rond
                'INPUT': self.inputExtent,
                'JOIN_STYLE': 0,  # Rond
                'MITER_LIMIT': 2,
                'SEGMENTS': 5,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.EXTENT_ZONE] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
        
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
                
            # Découper un raster selon une emprise
            alg_params = {
                'DATA_TYPE': 6,  # Float32
                'EXTRA': '',
                'INPUT': self.inputRasterMNT,
                'NODATA': 0,
                'OPTIONS': '',
                'OVERCRS': False,
                'PROJWIN': outputs[self.EXTENT_ZONE],
                'OUTPUT': self.outputRasterMNB
            }
            outputs[self.SLICED_RASTER] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

        # Extraire l'emprise de la couche
        alg_params = {
            'INPUT': outputs[self.SLICED_RASTER],
            'ROUND_TO': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RasterExtent'] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire par localisation
        # Filtre sur l'emprise
        alg_params = {
            'INPUT': parameters[self.BATI_INPUT],
            'INTERSECT': outputs[self.EXTENT_ZONE],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LocalisationBatiExtraction'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ attribut hauteur
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'height_field_bati',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': parameters[self.HEIGHT_FIELD_BATI],
            'INPUT': outputs['LocalisationBatiExtraction']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldHeightBati'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ hauteur mediane
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'median_h',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': ' median("height_field_bati")',
            'INPUT': outputs['CalculFieldHeightBati']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldHeightBatiMedian'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ remplacement hauteur NULL par mediane
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': parameters[self.HEIGHT_FIELD_BATI],
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': 'CASE\r\n\tWHEN  '+""+parameters[self.HEIGHT_FIELD_BATI]+""+' IS NULL THEN "median_h"\r\n\tELSE '+""+parameters[self.HEIGHT_FIELD_BATI]+""+'\r\nEND\r\n',
            'INPUT': outputs['CalculFieldHeightBatiMedian']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldHeightBatiReplaceNullByMedian'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Rastériser (remplacement avec attribut)
        alg_params = {
            'ADD': True,
            'EXTRA': '',
            'FIELD': parameters[self.HEIGHT_FIELD_BATI],
            'INPUT': outputs['CalculFieldHeightBatiReplaceNullByMedian']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER] #self.outputRasterMNB
        }
        outputs['RasteriseReplaceAttribute'] = processing.run('gdal:rasterize_over', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        self.results[self.OUTPUT_RASTER_MNB] = outputs['RasteriseReplaceAttribute']['OUTPUT']
        
        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Rasteriser (vecteur vers raster)
        # prendre la résolution du raster en hauteur/largeur
        alg_params = {
            'BURN': 0,
            'DATA_TYPE': 5,  # Float32
            'EXTENT': outputs['RasterExtent']['OUTPUT'],
            'EXTRA': '',
            'FIELD': parameters[self.HEIGHT_FIELD_BATI],
            'HEIGHT': self.inputRasterMNT.rasterUnitsPerPixelX(),
            'INIT': None,
            'INPUT': outputs['CalculFieldHeightBatiReplaceNullByMedian']['OUTPUT'],
            'INVERT': False,
            'NODATA': 0,
            'OPTIONS': '',
            'UNITS': 1,  # Unités géoréférencées
            'USE_Z': False,
            'WIDTH': self.inputRasterMNT.rasterUnitsPerPixelX(),
            'OUTPUT': self.outputRasterBati
        }
        outputs['RasteriserVecteurVersRaster'] = processing.run('gdal:rasterize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        self.results[self.OUTPUT_RASTER_BATI] = outputs['RasteriserVecteurVersRaster']['OUTPUT']
        
        print(step)
        return self.results

    def name(self):
        return self.tr('Calcul of MNB')

    def displayName(self):
        return self.tr('Calcul of MNB')

    def group(self):
        return  self.tr('Visibility Light Sources')

    def groupId(self):
        return  self.tr('Visibility Light Sources')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CalculMnb()

"""
Model exported as python.
Name : MNS
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


class CalculMNS(QgsProcessingAlgorithm):

    ALG_NAME = 'CalculMNS'
    
    RASTER_MNT_INPUT = 'MNT'
    BATI_INPUT = 'BatiBDTopo'
    VEGETATION_INPUT = 'VegetationBDTopo'
    EXTENT_ZONE = 'ExtentZone'
    HEIGHT_FIELD_BATI = 'HeightFieldBati'
    HEIGHT_FIELD_VEGETATION = 'HeightFieldVegetation'
    DEFAULT_HEIGHT_VEGETATION = 'DefaultHeightVegetation'
    SLICED_RASTER = 'SlicedRaster'
    OUTPUT_RASTER_MNS = 'OutputMNS'
    OUTPUT_RASTER_BATI = 'RasterBati'
    BUFFER_RADIUS = 'BufferRadius'
    
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_MNT_INPUT, self.tr('MNT'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.BUFFER_RADIUS, 'Radius of analysis for visibility (buffer of extent), meters', type=QgsProcessingParameterNumber.Double, defaultValue=500))
        
        self.addParameter(QgsProcessingParameterVectorLayer(self.BATI_INPUT, self.tr('Buildings (BD TOPO)'), types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterField(self.HEIGHT_FIELD_BATI, self.tr('Height Buildings fields'), type=QgsProcessingParameterField.Any, parentLayerParameterName=self.BATI_INPUT, allowMultiple=False, defaultValue='HAUTEUR'))
        
        self.addParameter(QgsProcessingParameterVectorLayer(self.VEGETATION_INPUT, self.tr('Vegetation'), types=[QgsProcessing.TypeVectorPolygon],optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterField(self.HEIGHT_FIELD_VEGETATION, self.tr('Height Vegetation field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.VEGETATION_INPUT, allowMultiple=False, defaultValue='HAUTEUR'))
        self.addParameter(QgsProcessingParameterNumber(self.DEFAULT_HEIGHT_VEGETATION, 'Height Vegetation by default if no field', optional=True, type=QgsProcessingParameterNumber.Double, defaultValue=6))
        
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_MNS, self.tr('MNS'), createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_BATI, self.tr('Raster bati vegetation'), createByDefault=True, defaultValue=None))
        
        # self.addParameter(QgsProcessingParameterVectorDestination('VegetationWithoutBati', 'vegetation', type=QgsProcessing.TypeVectorAnyGeometry,createByDefault=True, defaultValue=None)) # POUR TESTER

    def parseParams(self, parameters, context):
        self.inputExtent = self.parameterAsVectorLayer(parameters, self.EXTENT_ZONE, context)
        self.inputRasterMNT = self.parameterAsRasterLayer(parameters, self.RASTER_MNT_INPUT, context)
        self.inputBati = self.parameterAsVectorLayer(parameters, self.BATI_INPUT, context)
        self.inputVegetation = self.parameterAsVectorLayer(parameters, self.VEGETATION_INPUT, context)
        self.outputRasterMNS = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_MNS,context)
        self.outputRasterBati = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_BATI,context)
        
        # self.outputVegetation = self.parameterAsOutputLayer(parameters,'VegetationWithoutBati', context)
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(10, model_feedback)
       
        outputs = {}
        
        self.parseParams(parameters,context)
        
        # Extraire l'emprise de la couche
        # Si emprise non présente, on prend celle du MNS
        if self.inputExtent is None or self.inputExtent == NULL:
            alg_params = {
                    'INPUT': self.inputRasterMNT,
                    'ROUND_TO': 0,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
            outputs[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
        else:
            # Tampon
            alg_params = {
                'DISSOLVE': False,
                'DISTANCE': parameters[self.BUFFER_RADIUS], # doit être identique à la valeur de Light Points Extraction
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
            
        # Découper un raster selon une emprise
        alg_params = {
            'DATA_TYPE': 6,  # Float32
            'EXTRA': '',
            'INPUT': self.inputRasterMNT,
            'NODATA': 0,
            'OPTIONS': '',
            'OVERCRS': False,
            'PROJWIN': outputs[self.EXTENT_ZONE],
            'OUTPUT': self.outputRasterMNS
        }
        outputs[self.SLICED_RASTER] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire l'emprise de la couche raster, nécessaire pour rasterister ensuite
        alg_params = {
            'INPUT': outputs[self.SLICED_RASTER],
            'ROUND_TO': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RasterExtent'] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire par localisation le bati
        # Filtre sur l'emprise
        alg_params = {
            'INPUT': self.inputBati,
            'INTERSECT': outputs[self.EXTENT_ZONE],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LocalisationBatiExtraction'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ hauteur mediane
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'median_h',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': ' median("'+parameters[self.HEIGHT_FIELD_BATI]+'")',
            'INPUT': outputs['LocalisationBatiExtraction']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldHeightBatiMedian'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        step+=1
        feedback.setCurrentStep(step)
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
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Si la végétation est présente
        if self.inputVegetation is not None and self.inputVegetation != NULL and parameters[self.DEFAULT_HEIGHT_VEGETATION] is not None and parameters[self.DEFAULT_HEIGHT_VEGETATION] != NULL:
            if parameters[self.HEIGHT_FIELD_VEGETATION] is not None and parameters[self.HEIGHT_FIELD_VEGETATION] != NULL:
                # Extraire par attribut en enlevant les polygones sans hauteur
                alg_params = {
                    'FIELD': parameters[self.HEIGHT_FIELD_VEGETATION],
                    'INPUT': self.inputVegetation,
                    'OPERATOR': 9,  # n'est pas null
                    'VALUE': '',
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs['FilterVegetationWithHeight'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            else :
                outputs['FilterVegetationWithHeight'] = self.inputVegetation
                
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Extraction en fonction de l'emprise
            alg_params = {
                'INPUT': outputs['FilterVegetationWithHeight'],
                'INTERSECT': outputs[self.EXTENT_ZONE],
                'PREDICATE': [0],  # intersecte
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['LocalisationVegetationExtraction'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
        
           # Buffer de 5m autour du bati
            alg_params = {
                'DISSOLVE': False,
                'DISTANCE': 5,
                'END_CAP_STYLE': 0,  # Rond
                'INPUT': outputs['LocalisationBatiExtraction']['OUTPUT'],
                'JOIN_STYLE': 0,  # Rond
                'MITER_LIMIT': 2,
                'SEGMENTS': 5,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['BufferBati5m'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
           # Différence entre la végétation et le bati bufferisé pour enlever les zones qui se chevauches
            alg_params = {
                'INPUT': outputs['LocalisationVegetationExtraction']['OUTPUT'],
                'OVERLAY': outputs['BufferBati5m']['OUTPUT'] ,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['VegetationWithoutBati'] = processing.run('native:difference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Réparer les géométries
            alg_params = {
                'INPUT': outputs['VegetationWithoutBati']['OUTPUT'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['RepairVegetationWithoutBati'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
            
            if parameters[self.HEIGHT_FIELD_VEGETATION] is not None and parameters[self.HEIGHT_FIELD_VEGETATION] != NULL:
                formula = '"'+parameters[self.HEIGHT_FIELD_VEGETATION]+'"'
            else:
                formula = parameters[self.DEFAULT_HEIGHT_VEGETATION]
            # on ajoute le champ HAUTEUR temporaire à la végétation pour après la fusion
            alg_params = {
                'FIELD_LENGTH': 6,
                'FIELD_NAME': 'h_vegetation_temp',
                'FIELD_PRECISION': 2,
                'FIELD_TYPE': 0,  # Flottant
                'FORMULA': formula,
                'INPUT': outputs['RepairVegetationWithoutBati']['OUTPUT'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['RepairVegetationWithoutBati'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
           
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Union
            alg_params = {
                'INPUT': outputs['CalculFieldHeightBatiReplaceNullByMedian']['OUTPUT'],
                'OVERLAY': outputs['RepairVegetationWithoutBati']['OUTPUT'],
                'OVERLAY_FIELDS_PREFIX': '',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['VectorToRasterize'] = processing.run('native:union', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
             # on récupère le champ Hauteur temporaire de la végétation
            alg_params = {
                'FIELD_LENGTH': 6,
                'FIELD_NAME': parameters[self.HEIGHT_FIELD_BATI],
                'FIELD_PRECISION': 2,
                'FIELD_TYPE': 0,  # Flottant
                # 'FORMULA': '"h_vegetation_temp"',
                'FORMULA': 'CASE\r\n\tWHEN  '+""+parameters[self.HEIGHT_FIELD_BATI]+""+' IS NULL THEN "h_vegetation_temp"\r\n\tELSE '+""+parameters[self.HEIGHT_FIELD_BATI]+""+'\r\nEND\r\n',
                'INPUT': outputs['VectorToRasterize']['OUTPUT'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['VectorToRasterize'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            self.results['VectorToRasterize'] = outputs['VectorToRasterize']['OUTPUT']
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
            
        else: # on utilise seulement le bati
            outputs['VectorToRasterize'] = outputs['CalculFieldHeightBatiReplaceNullByMedian']
        
        
        # Rastériser (remplacement avec attribut)
        alg_params = {
            'ADD': True,
            'EXTRA': '',
            'FIELD': parameters[self.HEIGHT_FIELD_BATI],
            'INPUT': outputs['VectorToRasterize']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER] #self.outputRasterMNS
        }
        outputs['RasteriseReplaceAttribute'] = processing.run('gdal:rasterize_over', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        self.results[self.OUTPUT_RASTER_MNS] = outputs['RasteriseReplaceAttribute']['OUTPUT']
        
        step+=1
        feedback.setCurrentStep(step)
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
            'INPUT': outputs['VectorToRasterize']['OUTPUT'],
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
        return 'CalculMNS'

    def displayName(self):
        return self.tr('Calcul of MNS')

    def group(self):
        return  self.tr('Visibility Light Sources')

    def groupId(self):
        return  self.tr('Visibility Light Sources')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CalculMNS()

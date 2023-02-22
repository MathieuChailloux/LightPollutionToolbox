"""
Model exported as python.
Name : C1 P3 - Analyse niveau de radiance par maille
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
from qgis.core import QgsProcessingParameterVectorDestination
import processing


class StatisticsRadianceGrid(QgsProcessingAlgorithm):
    
    RASTER_INPUT = 'ImageJILINradianceRGB'
    SYMBOLOGY_STAT = 'SymbolStat'
    DIM_GRID = 'DiameterGrid'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    OUTPUT_STAT= 'OutputStat'
    
    SLICED_RASTER = 'SlicedRaster'
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Image JILIN radiance RGB'),defaultValue=None))
        self.addParameter(QgsProcessingParameterFile(self.SYMBOLOGY_STAT, self.tr('Apply a symbology to the result'), optional=True, behavior=QgsProcessingParameterFile.File, fileFilter=self.tr('Style file (*.qml)'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID, self.tr('Diameter grid (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, usesStaticStrings=False, defaultValue=2))
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT, self.tr('Statistics Radiance'), type=QgsProcessing.TypeVectorAnyGeometry))


    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 1
        feedback = QgsProcessingMultiStepFeedback(21, model_feedback)
        results = {}
        outputs = {}
        outputStat = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT,context)
        
        if parameters[self.EXTENT_ZONE] is None or parameters[self.EXTENT_ZONE] == NULL:
            # Extraire l'emprise de la couche raster
            # Si emprise non présente
            alg_params = {
                'INPUT': parameters[self.RASTER_INPUT],
                'ROUND_TO': 0,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            parameters[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
            outputs[self.SLICED_RASTER] = parameters[self.RASTER_INPUT] # le raster n'est pas découpé
            
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        else:
            # Découper un raster selon une emprise
            alg_params = {
                'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                'EXTRA': '',
                'INPUT': parameters[self.RASTER_INPUT],
                'NODATA': None,
                'OPTIONS': '',
                'OVERCRS': False,
                'PROJWIN': parameters[self.EXTENT_ZONE],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.SLICED_RASTER] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
            outputs[self.EXTENT_ZONE] = parameters[self.EXTENT_ZONE]

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

        # Créer une grille
        alg_params = {
            'CRS': parameters[self.EXTENT_ZONE],
            'EXTENT': parameters[self.EXTENT_ZONE],
            'HOVERLAY': 0,
            'HSPACING': parameters[self.DIM_GRID],
            'TYPE': parameters[self.TYPE_GRID]+2,  # Ajoute +2 pour aligner le bon type de grille
            'VOVERLAY': 0,
            'VSPACING': parameters[self.DIM_GRID],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridTemp'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
        
        # Extraire les grilles par localisation de l'emprise
        alg_params = {
            'INPUT': outputs['GridTemp']['OUTPUT'],
            'INTERSECT': parameters[self.EXTENT_ZONE],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridTempExtract'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
            
        # grille indexée
        alg_params = {
            'INPUT': outputs['GridTempExtract']['OUTPUT']
        }
        outputs['GridIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
            
        # Calculatrice Raster Radiance totale
        alg_params = {
            'BAND_A': 1,
            'BAND_B': 2,
            'BAND_C': 3,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*0.2989+B*0.5870+C*0.1140',
            'INPUT_A': outputs[self.SLICED_RASTER],
            'INPUT_B': outputs[self.SLICED_RASTER],
            'INPUT_C': outputs[self.SLICED_RASTER],
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculRasterTotalRadiance'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice Raster Segmentation
        # Si rad totale > mediane+1 : 1 sinon 0
        alg_params = {
            'BAND_A': 1,
            'BAND_B': None,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': '1*(logical_or(A>(median(A)+1) , False))',
            'INPUT_A': outputs['CalculRasterTotalRadiance']['OUTPUT'],
            'INPUT_B': None,
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculRasterSegmentation'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Polygoniser zone éclairée
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': outputs['CalculRasterSegmentation']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygoniseLightZone'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire zone éclairée
        alg_params = {
            'FIELD': 'DN',
            'INPUT': outputs['PolygoniseLightZone']['OUTPUT'],
            'OPERATOR': 0,  # =
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractLightZone'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Réparer les géométries
        alg_params = {
            'INPUT': outputs['ExtractLightZone']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RepairGeom'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # zones éclairées indexées
        alg_params = {
            'INPUT': outputs['RepairGeom']['OUTPUT']
        }
        outputs['LightZoneIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire par maille non éclairée
        alg_params = {
            'INPUT': outputs['GridIndex']['OUTPUT'],
            'INTERSECT': outputs['LightZoneIndex']['OUTPUT'],
            'PREDICATE': [2],  # est disjoint
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractDarkGrid'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ indice radiance null
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'indice_pol',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Entier
            'FORMULA': '0',
            'INPUT': outputs['ExtractDarkGrid']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldIndiceRadianceNull'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire maille éclairée
        alg_params = {
            'INPUT': outputs['GridIndex']['OUTPUT'],
            'INTERSECT': outputs['LightZoneIndex']['OUTPUT'],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractLightGrid'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande rouge
        alg_params = {
            'COLUMN_PREFIX': 'R_',
            'INPUT': outputs['ExtractLightGrid']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER],
            'RASTER_BAND': 1,
            'STATISTICS': [1,2],  # Somme,Moyenne
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsRedBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande verte
        alg_params = {
            'COLUMN_PREFIX': 'V_',
            'INPUT': outputs['StatisticsRedBand']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER],
            'RASTER_BAND': 2,
            'STATISTICS': [1,2],  # Somme,Moyenne
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsGreenBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande bleu
        alg_params = {
            'COLUMN_PREFIX': 'B_',
            'INPUT': outputs['StatisticsGreenBand']['OUTPUT'],
            'INPUT_RASTER': outputs[self.SLICED_RASTER],
            'RASTER_BAND': 3,
            'STATISTICS': [1,2],  # Somme,Moyenne
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsBlueBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone radiance totale
        alg_params = {
            'COLUMN_PREFIX': 'tot_',
            'INPUT': outputs['StatisticsBlueBand']['OUTPUT'],
            'INPUT_RASTER': outputs['CalculRasterTotalRadiance']['OUTPUT'],
            'RASTER_BAND': 1,
            'STATISTICS': [1,2],  # Somme,Moyenne
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsZoneTotalRadiance'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ indice radiance
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'indice_pol',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Entier
            'FORMULA': 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("tot_mean",order_by:="tot_mean"),"tot_mean") / array_length(array_agg("tot_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 1\r\n    WHEN @percentile < 0.4 THEN 2\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 4\r\n    WHEN @percentile <= 1 THEN 5\r\n    ELSE 0\r\n    END\r\n)',
            'INPUT': outputs['StatisticsZoneTotalRadiance']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldIndiceRadiance'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Fusionner des couches vecteur (grilles avec radiance et grilles sans radiance)
        alg_params = {
            'CRS': outputs['CalculFieldIndiceRadiance']['OUTPUT'],
            'LAYERS': [outputs['CalculFieldIndiceRadiance']['OUTPUT'],outputs['CalculFieldIndiceRadianceNull']['OUTPUT']],
            'OUTPUT': outputStat
        }
        outputs['MergeVectorLayer'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results[self.OUTPUT_STAT] = outputs['MergeVectorLayer']['OUTPUT']

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
        
        if parameters[self.SYMBOLOGY_STAT] is not None and parameters[self.SYMBOLOGY_STAT] != NULL: # vérifie si la symbologie est entrée
            # Définir le style de la couche résutlat
            alg_params = {
                'INPUT': outputs['MergeVectorLayer']['OUTPUT'],
                'STYLE': parameters[self.SYMBOLOGY_STAT]
            }
            outputs['setStyleLayerRes'] = processing.run('native:setlayerstyle', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        
        print(step)
        return results

    def name(self):
        return self.tr('Statistics of radiance per grid')

    def displayName(self):
        return self.tr('Statistics of radiance per grid')
        
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
        return StatisticsRadianceGrid()
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
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles

class StatisticsRadianceGrid(QgsProcessingAlgorithm):
    
    RASTER_INPUT = 'ImageJILINradianceRGB'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    DIM_GRID = 'GridDiameter'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    OUTPUT_STAT = 'OutputStat'
    
    # MAJORITY_FIELD = "_majority"

    
    SLICED_RASTER = 'SlicedRaster'
    
    IND_FIELD_POL = 'indice_pol'
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Image JILIN radiance RGB'),defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID, self.tr('Grid diameter (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, usesStaticStrings=False, defaultValue=2))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT, self.tr('Statistics Radiance'), type=QgsProcessing.TypeVectorAnyGeometry))
                
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
        self.outputStat = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT,context)
       
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 1
        feedback = QgsProcessingMultiStepFeedback(21, model_feedback)
        
        outputs = {}
        
        self.parseParams(parameters,context)
        
        if self.inputExtent is None or self.inputExtent == NULL:
            # Extraire l'emprise de la couche raster
            # Si emprise non présente
            alg_params = {
                'INPUT': self.inputRaster,
                'ROUND_TO': 0,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
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

        # Créer une grille
        alg_params = {
            'CRS': outputs[self.EXTENT_ZONE],
            'EXTENT': outputs[self.EXTENT_ZONE],
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
            'INTERSECT': outputs[self.EXTENT_ZONE],
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
        
        # ########################################################################## PRETRAITEMENTS A SORTIR ##########################################################################
        
        # # Statistiques de zone pour les 3 bandes afin de récupérer les pixels majoritaires
        # majorityBand1 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        # majorityBand2 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.GREEN_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        # majorityBand3 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.BLUE_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)

        # # Calculatrice Raster masque pour enlever les zones non éclairées
        # # Si les 3 pixels des 3 bandes < majortité+1 alors 0, sinon 1 
        # # Ici la condition indique l'inverse : pour mettre les pixels à 1, il faut qu'au moins 1 des 3 soit > majorité
        # alg_params = {
            # 'BAND_A': parameters[self.RED_BAND_INPUT], #1
            # 'BAND_B': parameters[self.GREEN_BAND_INPUT], #2
            # 'BAND_C': parameters[self.BLUE_BAND_INPUT], #3
            # 'BAND_D': None,
            # 'BAND_E': None,
            # 'BAND_F': None,
            # 'EXTRA': '',
            # 'FORMULA': '1*logical_or(logical_or((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')), (C >'+str(majorityBand3)+'))',
            # 'INPUT_A': outputs[self.SLICED_RASTER],
            # 'INPUT_B': outputs[self.SLICED_RASTER],
            # 'INPUT_C': outputs[self.SLICED_RASTER],
            # 'INPUT_D': None,
            # 'INPUT_E': None,
            # 'INPUT_F': None,
            # 'NO_DATA': None,
            # 'OPTIONS': '',
            # 'RTYPE': 1,  # Int16
            # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        # }
        # outputs['CalculRasterMask'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # feedback.setCurrentStep(step)
        # step+=1
        # if feedback.isCanceled():
            # return {}
        
        # # Calculatrice Raster B1 avec masque
        # alg_params = {
            # 'BAND_A': parameters[self.RED_BAND_INPUT],
            # 'BAND_B': 1,
            # 'BAND_C': None,
            # 'BAND_D': None,
            # 'BAND_E': None,
            # 'BAND_F': None,
            # 'EXTRA': '',
            # 'FORMULA': 'A*B',
            # 'INPUT_A': outputs[self.SLICED_RASTER],
            # 'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],
            # 'INPUT_C': None,
            # 'INPUT_D': None,
            # 'INPUT_E': None,
            # 'INPUT_F': None,
            # 'NO_DATA': None,
            # 'OPTIONS': '',
            # 'RTYPE': 5,  # Float32
            # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        # }
        # outputs['CalculRasterB1'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # feedback.setCurrentStep(step)
        # step+=1
        # if feedback.isCanceled():
            # return {}
            
        # # Calculatrice Raster B2 avec masque
        # alg_params = {
            # 'BAND_A': parameters[self.GREEN_BAND_INPUT],
            # 'BAND_B': 1,
            # 'BAND_C': None,
            # 'BAND_D': None,
            # 'BAND_E': None,
            # 'BAND_F': None,
            # 'EXTRA': '',
            # 'FORMULA': 'A*B',
            # 'INPUT_A': outputs[self.SLICED_RASTER],
            # 'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],
            # 'INPUT_C': None,
            # 'INPUT_D': None,
            # 'INPUT_E': None,
            # 'INPUT_F': None,
            # 'NO_DATA': None,
            # 'OPTIONS': '',
            # 'RTYPE': 5,  # Float32
            # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        # }
        # outputs['CalculRasterB2'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # feedback.setCurrentStep(step)
        # step+=1
        # if feedback.isCanceled():
            # return {}
            
        # # Calculatrice Raster B3 avec masque
        # alg_params = {
            # 'BAND_A': parameters[self.BLUE_BAND_INPUT],
            # 'BAND_B': 1,
            # 'BAND_C': None,
            # 'BAND_D': None,
            # 'BAND_E': None,
            # 'BAND_F': None,
            # 'EXTRA': '',
            # 'FORMULA': 'A*B',
            # 'INPUT_A': outputs[self.SLICED_RASTER],
            # 'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],
            # 'INPUT_C': None,
            # 'INPUT_D': None,
            # 'INPUT_E': None,
            # 'INPUT_F': None,
            # 'NO_DATA': None,
            # 'OPTIONS': '',
            # 'RTYPE': 5,  # Float32
            # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        # }
        # outputs['CalculRasterB3'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # feedback.setCurrentStep(step)
        # step+=1
        # if feedback.isCanceled():
            # return {}
        
        # ##############################################################################################################################################################################################################################
        
        
        # Calculatrice Raster Radiance totale
        alg_params = {
            'BAND_A': parameters[self.RED_BAND_INPUT], #1
            'BAND_B': parameters[self.GREEN_BAND_INPUT], #1
            'BAND_C': parameters[self.BLUE_BAND_INPUT], #1
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*0.2989+B*0.5870+C*0.1140',
            'INPUT_A': outputs[self.SLICED_RASTER], #outputs['CalculRasterB1']['OUTPUT']
            'INPUT_B': outputs[self.SLICED_RASTER], #outputs['CalculRasterB1']['OUTPUT']
            'INPUT_C': outputs[self.SLICED_RASTER], #outputs['CalculRasterB1']['OUTPUT']
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
            'FIELD_NAME': self.IND_FIELD_POL,
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
            'INPUT_RASTER': outputs[self.SLICED_RASTER], #outputs['CalculRasterB1']['OUTPUT'],
            'RASTER_BAND': parameters[self.RED_BAND_INPUT], #1,
            'STATISTICS': [0,1,2],  # Count, Somme,Moyenne
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
            'INPUT_RASTER': outputs[self.SLICED_RASTER], # outputs['CalculRasterB2']['OUTPUT'],
            'RASTER_BAND': parameters[self.GREEN_BAND_INPUT], #1,
            'STATISTICS': [0,1,2],  # Count, Somme,Moyenne
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
            'INPUT_RASTER': outputs[self.SLICED_RASTER], #outputs['CalculRasterB3']['OUTPUT'],
            'RASTER_BAND': parameters[self.BLUE_BAND_INPUT], #1, 
            'STATISTICS': [0,1,2],  # Count, Somme,Moyenne
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
            'FIELD_NAME': self.IND_FIELD_POL,
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
            'OUTPUT': self.outputStat
        }
        outputs['MergeVectorLayer'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        self.results[self.OUTPUT_STAT] = outputs['MergeVectorLayer']['OUTPUT']

        
        print(step)
        return self.results

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

    def postProcessAlgorithm(self,context,feedback):
        out_layer = QgsProcessingUtils.mapLayerFromString(self.results[self.OUTPUT_STAT],context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.results[self.OUTPUT_STAT]))
        
        # Applique la symbologie par défault
        styles.setCustomClassesInd_Pol(out_layer, self.IND_FIELD_POL)
        return self.results

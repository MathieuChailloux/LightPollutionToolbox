"""
Model exported as python.
Name : Analyse blue emission per grid
Group : ASE
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingUtils
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles



class StatisticsBlueEmissionGrid(QgsProcessingAlgorithm):
    RASTER_INPUT = 'ImageJILINradianceRGB'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    SYMBOLOGY_STAT = 'SymbolStat'
    DIM_GRID_CALC = 'DiameterGridCalcul'
    DIM_GRID_RES = 'DiameterGridResultat'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    OUTPUT_STAT_CALC = 'OutputStatCalcul'
    OUTPUT_STAT_RES = 'OutputStatResult'
    
    MAJORITY_FIELD = "_majority"
    
    
    SLICED_RASTER = 'SlicedRaster'
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Image JILIN radiance RGB'),defaultValue=None))
        self.addParameter(QgsProcessingParameterFile(self.SYMBOLOGY_STAT, self.tr('Apply a symbology to the result'), optional=True, behavior=QgsProcessingParameterFile.File, fileFilter=self.tr('Style file (*.qml)'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID_CALC, self.tr('Diameter grid calcul (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=150))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID_RES, self.tr('Diameter grid result (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, usesStaticStrings=False, defaultValue=2))
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT_CALC, self.tr('statistics blue emission'), type=QgsProcessing.TypeVectorAnyGeometry))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT_RES, self.tr('statistics blue emission 50m'), type=QgsProcessing.TypeVectorAnyGeometry))
                
        param = QgsProcessingParameterNumber(self.RED_BAND_INPUT, self.tr('Index of the red band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=1)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.GREEN_BAND_INPUT, self.tr('Index of the green band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=2)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.BLUE_BAND_INPUT, self.tr('Index of the blue band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=3)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 1
        feedback = QgsProcessingMultiStepFeedback(19, model_feedback)

        results = {}
        outputs = {}
       
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
            # Découper un raster selon l'emprise
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

        if parameters[self.DIM_GRID_CALC] != parameters[self.DIM_GRID_RES]: # uniquement sur les 2 grilles sont de taille différente
            # Créer une grille de résultat
            alg_params = {
                'CRS': parameters[self.EXTENT_ZONE],
                'EXTENT': parameters[self.EXTENT_ZONE],
                'HOVERLAY': 0,
                'HSPACING': parameters[self.DIM_GRID_RES],
                'TYPE': parameters[self.TYPE_GRID]+2,  # Ajoute +2 pour aligner le bon type de grille
                'VOVERLAY': 0,
                'VSPACING': parameters[self.DIM_GRID_RES],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['GridTempRes'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            feedback.setCurrentStep(step)
            step+=1
            
            # Extraire les grilles resultat par localisation de l'emprise
            alg_params = {
                'INPUT': outputs['GridTempRes']['OUTPUT'],
                'INTERSECT': parameters[self.EXTENT_ZONE],
                'PREDICATE': [0],  # intersecte
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['GridTempResExtract'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

            # grille résultat indexée
            alg_params = {
                'INPUT': outputs['GridTempResExtract']['OUTPUT']
            }
            outputs['GridTempResIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

        # Créer une grille de calcul
        alg_params = {
            'CRS': parameters[self.EXTENT_ZONE],
            'EXTENT': parameters[self.EXTENT_ZONE],
            'HOVERLAY': 0,
            'HSPACING': parameters[self.DIM_GRID_CALC],
            'TYPE': parameters[self.TYPE_GRID]+2,  # Ajoute +2 pour aligner le bon type de grille
            'VOVERLAY': 0,
            'VSPACING': parameters[self.DIM_GRID_CALC],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridTempCalc'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire les grilles de calcul par localisation de l'emprise
        alg_params = {
            'INPUT': outputs['GridTempCalc']['OUTPUT'],
            'INTERSECT': parameters[self.EXTENT_ZONE],
            'PREDICATE': [0],  # intersecte
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridTempCalcExtract'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # grille de calcul indexée
        alg_params = {
            'INPUT': outputs['GridTempCalcExtract']['OUTPUT']
        }
        outputs['GridTempCalcIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}


        # Statistiques de zone pour les 3 bandes afin de récupérer les pixels majoritaires
        majorityBand1 = qgsTreatments.getMajorityValue(parameters[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        majorityBand2 = qgsTreatments.getMajorityValue(parameters[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.GREEN_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        majorityBand3 = qgsTreatments.getMajorityValue(parameters[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.BLUE_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        
        # Calculatrice Raster masque pour enlever les zones non éclairées
        alg_params = {
            'BAND_A': parameters[self.RED_BAND_INPUT], #1
            'BAND_B': parameters[self.GREEN_BAND_INPUT], #2
            'BAND_C': parameters[self.BLUE_BAND_INPUT], #3
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': '1*logical_and(logical_and((A>='+str(majorityBand1+1)+'), (B>='+str(majorityBand2+1)+')), (C >='+str(majorityBand3+1)+'))',
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
        
        feedback.setCurrentStep(1)
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
            'INPUT_B': outputs['CalculRasterMask']['OUTPUT'],#parameters['masquezonesombre'],
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
        
        
        # Statistiques de zone bande rouge
        alg_params = {
            'COLUMN_PREFIX': 'R_',
            'INPUT': outputs['GridTempCalcIndex']['OUTPUT'],
            'INPUT_RASTER': outputs['CalculRasterB1']['OUTPUT'], #outputs[self.SLICED_RASTER],
            'RASTER_BAND': 1,
            'STATISTICS': [1,2,3,4],  # Somme,Moyenne, Médiane, Ecart-type
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsRedBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

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
            'INPUT_B': outputs['CalculRasterMask']['OUTPUT'], #parameters['masquezonesombre'],
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
        
        # Statistiques de zone bande bleu
        alg_params = {
            'COLUMN_PREFIX': 'B_',
            'INPUT': outputs['StatisticsRedBand']['OUTPUT'],
            'INPUT_RASTER': outputs['CalculRasterB3']['OUTPUT'], #outputs[self.SLICED_RASTER],
            'RASTER_BAND': 1,
            'STATISTICS': [1,2,3,4],  # Somme,Moyenne, Médiane, Ecart-type
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['StatisticsBlueBand'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calcul champ R/B_mean
        # NULL si R_mean ou B_mean = 0
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'R/B_mean',
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': 'CASE\r\n\tWHEN "R_mean" = 0 or "B_mean" = 0 THEN NULL\r\n\tELSE "R_mean"/"B_mean"\r\nEND',# TEST INDICE NORMALISE B-R/B+R : ("B_mean"-"R_mean")/("B_mean"+"R_mean")
            'INPUT': outputs['StatisticsBlueBand']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldRb_mean'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calcul champ R/B_Q3
        # NULL si R_mean ou B_mean = 0
        # TODO : trouver comment récupérer le q3 du raster
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'R/B_Q3',
            'FIELD_PRECISION': 4,
            'FIELD_TYPE': 0,  # Flottant
            'FORMULA': 'CASE\r\n\tWHEN "R_stdev" = 0 or "B_stdev" = 0 THEN NULL\r\n\tELSE "R_stdev"/"B_stdev"\r\nEND',
            'INPUT': outputs['CalculFieldRb_mean']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculFieldRb_q3'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ indice bleu pour la couche de calcul
        # quantiles inversés
        outputStatCalc = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT_CALC,context)
        alg_params = {
            'FIELD_LENGTH': 6,
            'FIELD_NAME': 'indice_pol',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Entier
            'FORMULA': 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("R/B_mean",order_by:="R/B_mean"),"R/B_mean") / array_length(array_agg("R/B_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 5\r\n    WHEN @percentile < 0.4 THEN 4\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 2\r\n    WHEN @percentile <= 1 THEN 1\r\n    ELSE 0\r\n    END\r\n)',
            'INPUT': outputs['CalculFieldRb_q3']['OUTPUT'],
            'OUTPUT': outputStatCalc
        }
        outputs['CalculFieldIndicatorCalc'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results[self.OUTPUT_STAT_CALC] = outputs['CalculFieldIndicatorCalc']['OUTPUT']

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}
        
        if parameters[self.DIM_GRID_CALC] != parameters[self.DIM_GRID_RES]: # uniquement sur les 2 grilles sont de taille différente
            # Joindre les attributs par localisation (résumé)
            # Intersection entre les grilles de calcul et de résultat
            alg_params = {
                'DISCARD_NONMATCHING': False,
                'INPUT': outputs['GridTempResIndex']['OUTPUT'],
                'JOIN': outputs['CalculFieldRb_q3']['OUTPUT'],
                'JOIN_FIELDS': [''],
                'PREDICATE': [0],  # intersecte
                'SUMMARIES': [6],  # mean
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['JoinFieldsLocalisationCalculResult'] = processing.run('qgis:joinbylocationsummary', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        
            # Calculatrice de champ indice bleu pour la couche de résultat
            # quantiles inversés
            outputStatRes = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT_RES,context)
            alg_params = {
                'FIELD_LENGTH': 6,
                'FIELD_NAME': 'indice_pol',
                'FIELD_PRECISION': 0,
                'FIELD_TYPE': 1,  # Entier
                'FORMULA': 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("R/B_mean_mean",order_by:="R/B_mean_mean"),"R/B_mean_mean") / array_length(array_agg("R/B_mean_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 5\r\n    WHEN @percentile < 0.4 THEN 4\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 2\r\n    WHEN @percentile <= 1 THEN 1\r\n    ELSE 0\r\n    END\r\n)',
                'INPUT': outputs['JoinFieldsLocalisationCalculResult']['OUTPUT'],
                'OUTPUT': outputStatRes
            }
            outputs['CalculFieldIndicatorRes'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            results[self.OUTPUT_STAT_RES] = outputs['CalculFieldIndicatorRes']['OUTPUT']

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
            
            if parameters[self.SYMBOLOGY_STAT] is not None and parameters[self.SYMBOLOGY_STAT] != NULL: # vérifie si la symbologie est entrée
                # Définir le style de la couche résutlat
                alg_params = {
                    'INPUT': outputs['CalculFieldIndicatorRes']['OUTPUT'],
                    'STYLE': parameters[self.SYMBOLOGY_STAT]
                }
                outputs['setStyleLayerResult'] = processing.run('native:setlayerstyle', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                feedback.setCurrentStep(step)
                step+=1
                feedback.setCurrentStep(step)
            
        
        if parameters[self.SYMBOLOGY_STAT] is not None and parameters[self.SYMBOLOGY_STAT] != NULL: # vérifie si la symbologie est entrée
            # Définir le style de la couche calcul
            alg_params = {
                'INPUT': outputs['CalculFieldIndicatorCalc']['OUTPUT'],
                'STYLE': parameters[self.SYMBOLOGY_STAT]
            }
            outputs['setStyleLayerCalcul'] = processing.run('native:setlayerstyle', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        
        print(step)
        return results
        

    def name(self):
        return self.tr('Statistics of blue emission per grid')

    def displayName(self):
        return self.tr('Statistics of blue emission per grid')

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
        return StatisticsBlueEmissionGrid()

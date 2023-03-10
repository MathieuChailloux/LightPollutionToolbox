"""
Model exported as python.
Name : analyse visibilité hors bati MNB
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
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterRasterDestination
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles


class AnalyseVisibilityLightSources(QgsProcessingAlgorithm):

    ALG_NAME = 'AnalyseVisibilityLightSources'
    
    VIEWSHED_INPUT = 'ViewshedInput'
    EXTENT_ZONE = 'ExtentZone'
    MASK_HEIGHT = 'MaskHeight'
    BUILDINGS_MASK = 'BuildingsMask'
    DIM_GRID = 'GridDiameter'
    TYPE_GRID = 'TypeOfGrid'
    RASTER_BATI_INPUT = 'RasterBatiInput'
    GRID_LAYER_INPUT = 'GridLayerInput'
    SLICED_RASTER_VIEWSHED = 'SlicedRasterViewshed'
    SLICED_RASTER_BATI = 'SlicedRasterBati'
    OUTPUT_BUILDINGS_MASK = 'OutputBuildingsMask'
    OUTPUT_NB_SRC_VIS = 'OutputNbSrcVis'
    
    FIELD_STYLE = '_mean'
    CLASS_BOUNDS_NB_SRC = [0,5,10,20,50]
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.VIEWSHED_INPUT, self.tr('Layer resulting from viewshed processing'), defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_BATI_INPUT, self.tr('Raster bati'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.MASK_HEIGHT, self.tr('Mask height'), type=QgsProcessingParameterNumber.Double, defaultValue=1))
        
        self.addParameter(QgsProcessingParameterVectorLayer(self.GRID_LAYER_INPUT, self.tr('Grid Layer'), optional=True, defaultValue=None))
        
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID, self.tr('Grid diameter (meter) if no grid layer'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid if no grid layer'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, usesStaticStrings=False, defaultValue=2))
        
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_BUILDINGS_MASK, self.tr('Buildings mask'), createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_NB_SRC_VIS, self.tr('Analyse par maille du nombre de sources visibles'), type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
    
    def parseParams(self, parameters, context):
        self.inputExtent = self.parameterAsVectorLayer(parameters, self.EXTENT_ZONE, context)
        self.inputViewshed = self.parameterAsRasterLayer(parameters, self.VIEWSHED_INPUT, context)
        self.inputRasterBati = self.parameterAsRasterLayer(parameters, self.RASTER_BATI_INPUT, context)
        self.inputGrid = self.parameterAsVectorLayer(parameters, self.GRID_LAYER_INPUT, context)
        self.outputBuildingsMarsk = self.parameterAsOutputLayer(parameters,self.OUTPUT_BUILDINGS_MASK, context)
        self.outputNbSrcVis = self.parameterAsOutputLayer(parameters,self.OUTPUT_NB_SRC_VIS, context)
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(10, model_feedback)
        outputs = {}
        
        self.parseParams(parameters,context)
        
        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Si grille non présente prendre l'emprise de la couche raster Viewshed
            if self.inputGrid is None or self.inputGrid == NULL:
                alg_params = {
                    'INPUT': self.inputViewshed,
                    'ROUND_TO': 0,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs[self.EXTENT_ZONE] = processing.run('native:polygonfromlayerextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
                outputs[self.SLICED_RASTER_VIEWSHED] = self.inputViewshed # le raster n'est pas découpé
                # le raster bati est découpé pour avoir la même taille que le viewshed
                # Découper le raster Bati selon une emprise (celle de la grille)
                alg_params = {
                    'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                    'EXTRA': '',
                    'INPUT': self.inputRasterBati,
                    'NODATA': None,
                    'OPTIONS': '',
                    'OVERCRS': False,
                    'PROJWIN': outputs[self.EXTENT_ZONE],
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs[self.SLICED_RASTER_BATI] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
                
                feedback.setCurrentStep(step)
                step+=1
                if feedback.isCanceled():
                    return {}
             # Sinon prendre l'emprise de la grille
            else:
                # Découper le raster Viewshed selon une emprise (celle de la grille)
                alg_params = {
                    'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                    'EXTRA': '',
                    'INPUT': self.inputViewshed,
                    'NODATA': None,
                    'OPTIONS': '',
                    'OVERCRS': False,
                    'PROJWIN': self.inputGrid,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs[self.SLICED_RASTER_VIEWSHED] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
                outputs[self.EXTENT_ZONE] = self.inputGrid
                
                feedback.setCurrentStep(step)
                step+=1
                if feedback.isCanceled():
                    return {}
                
                # Découper le raster Bati selon une emprise (celle de la grille)
                alg_params = {
                    'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                    'EXTRA': '',
                    'INPUT': self.inputRasterBati,
                    'NODATA': None,
                    'OPTIONS': '',
                    'OVERCRS': False,
                    'PROJWIN': self.inputGrid,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                outputs[self.SLICED_RASTER_BATI] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
                
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        else:
            # Découper le raster Viewshed selon une emprise
            alg_params = {
                'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                'EXTRA': '',
                'INPUT': self.inputViewshed,
                'NODATA': None,
                'OPTIONS': '',
                'OVERCRS': False,
                'PROJWIN': self.inputExtent,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.SLICED_RASTER_VIEWSHED] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            outputs[self.EXTENT_ZONE] = self.inputExtent

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
                
            # Découper le raster Bati selon une emprise
            alg_params = {
                'DATA_TYPE': 0,  # Utiliser le type de donnée de la couche en entrée
                'EXTRA': '',
                'INPUT': self.inputRasterBati,
                'NODATA': None,
                'OPTIONS': '',
                'OVERCRS': False,
                'PROJWIN': self.inputExtent,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs[self.SLICED_RASTER_BATI] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
            
            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}

        if self.inputGrid is None or self.inputGrid == NULL:
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
            outputs['GridTemp'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']

            feedback.setCurrentStep(step)
            step+=1
            if feedback.isCanceled():
                return {}
        else:
        # Sinon on prend la grille donnée en paramètre
            outputs['GridTemp'] = self.inputGrid
            

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Extraire la grille par localisation de l'emprise
        alg_params = {
            'INPUT': outputs['GridTemp'],
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

        # Calculatrice Raster enleve bati haut
        # Masque bati
        #Si hauteur > h_remplie  : 0 Sinon 1
        alg_params = {
            'BAND_A': 1,
            'BAND_B': None, #1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': '1*(logical_and(A<= '+str(parameters[self.MASK_HEIGHT])+', True))', #'1*(logical_and(A<= B, True))',
            'INPUT_A': outputs[self.SLICED_RASTER_BATI],
            'INPUT_B': None, #outputs['CrerUneCoucheRasterConstantePourLaHauteurDuMasque']['OUTPUT'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': self.outputBuildingsMarsk
        }
        self.results[self.OUTPUT_BUILDINGS_MASK] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Remplir les cellules sans données
        alg_params = {
            'BAND': 1,
            'FILL_VALUE': 1,
            'INPUT': self.outputBuildingsMarsk,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FillCellsWithoutData'] = processing.run('native:fillnodata', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Mise à zéro du pixel sur bati supérieur à une certaine hauteur
        alg_params = {
            'BAND_A': 1,
            'BAND_B': 1,
            'BAND_C': None,
            'BAND_D': None,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': 'A*B',
            'INPUT_A': outputs[self.SLICED_RASTER_VIEWSHED],
            'INPUT_B': outputs['FillCellsWithoutData']['OUTPUT'],
            'INPUT_C': None,
            'INPUT_D': None,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,  # Float32
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['BatiWithHeightMask'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(step)
        step+=1
        if feedback.isCanceled():
            return {}

        # Statistiques de zone (moyenne)
        alg_params = {
            'COLUMN_PREFIX': '_',
            'INPUT': outputs['GridIndex']['OUTPUT'],
            'INPUT_RASTER': outputs['BatiWithHeightMask']['OUTPUT'],
            'RASTER_BAND': 1,
            'STATISTICS': [2,4],  # Moyenne,Ecart-type
            'OUTPUT': self.outputNbSrcVis
        }
        self.results[self.OUTPUT_NB_SRC_VIS] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
        
        print(step)
        
        return self.results

    def name(self):
        return 'AnalyseVisibilityLightSources'

    def displayName(self):
        return self.tr('Number sources of light visibility per grid')
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def group(self):
        return  self.tr('Visibility Light Sources')

    def groupId(self):
        return  self.tr('Visibility Light Sources')

    def createInstance(self):
        return AnalyseVisibilityLightSources()
        
    def postProcessAlgorithm(self,context,feedback):
        out_layer = QgsProcessingUtils.mapLayerFromString(self.results[self.OUTPUT_NB_SRC_VIS],context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.results[self.OUTPUT_NB_SRC_VIS]))
        
        # Applique la symbologie par défault
        
        color_ramp = styles.getColorBrewColorRampGnYlRd()
        styles.setCustomClasses2(out_layer,'_mean',color_ramp, self.CLASS_BOUNDS_NB_SRC) # ne permet pas d'avoir des bordures transparentes
        
        # styles.setCustomClassesInd_Pol(out_layer, self.FIELD_STYLE, self.CLASS_BOUNDS_NB_SRC) # affecte une couleur par valeur, pas par tranche : changer la fonction ?
        
        return self.results

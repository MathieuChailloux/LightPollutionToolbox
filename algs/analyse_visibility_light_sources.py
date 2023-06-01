"""
Model exported as python.
Name : analyse visibilité hors bati et végétation MNS
Group : Visibility Light Sources
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import Qgis
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
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingException
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
    LAST_BOUNDS = 'LastBounds'
    SLICED_RASTER_VIEWSHED = 'SlicedRasterViewshed'
    SLICED_RASTER_BATI = 'SlicedRasterBati'
    OUTPUT_BUILDINGS_MASK = 'OutputBuildingsMask'
    OUTPUT_NB_SRC_RASTER = 'OutputNbSrcRaster'
    OUTPUT_NB_SRC_VIS = 'OutputNbSrcVis'
    
    FIELD_STYLE = '_mean'
    CLASS_BOUNDS_NB_SRC = [0,0,5,10,20,50] # on double la valeur 0 pour avoir un premier pas avec uniquement ces valeurs
    LAST_BOUNDS_VALUE = 50
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterRasterLayer(self.VIEWSHED_INPUT, self.tr('Layer resulting from viewshed processing'), defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_BATI_INPUT, self.tr('Raster bati'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.MASK_HEIGHT, self.tr('Mask height'), type=QgsProcessingParameterNumber.Double, defaultValue=1))
        
        self.addParameter(QgsProcessingParameterFeatureSource(self.GRID_LAYER_INPUT, self.tr('Grid Layer'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
                
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID, self.tr('Grid diameter (meter) if no grid layer'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid if no grid layer'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, defaultValue=2))
        
        self.addParameter(QgsProcessingParameterNumber(self.LAST_BOUNDS, self.tr('Bounds for the last class of symbology'), type=QgsProcessingParameterNumber.Double, defaultValue=50))

        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_NB_SRC_RASTER, self.tr('Output Raster Number of visible lights'), createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_NB_SRC_VIS, self.tr('Output Number of visible lights per grid'), type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
    
    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1] 
        self.inputViewshed = self.parameterAsRasterLayer(parameters, self.VIEWSHED_INPUT, context)
        self.inputRasterBati = self.parameterAsRasterLayer(parameters, self.RASTER_BATI_INPUT, context)
        self.inputGrid = qgsTreatments.parameterAsSourceLayer(self, parameters,self.GRID_LAYER_INPUT,context,feedback=feedback)[1] 
        self.outputbSrcRaster = self.parameterAsOutputLayer(parameters,self.OUTPUT_NB_SRC_RASTER, context)
        self.outputNbSrcVis = self.parameterAsOutputLayer(parameters,self.OUTPUT_NB_SRC_VIS, context)
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
        outputs = {}
        
        self.parseParams(parameters, context, feedback)  
        
        # Test projection des input sont bien en unité métrique
        if self.inputExtent is not None or self.inputExtent != NULL:
            qgsUtils.checkProjectionUnit(self.inputExtent)
        qgsUtils.checkProjectionUnit(self.inputViewshed)
        qgsUtils.checkProjectionUnit(self.inputRasterBati)
        if self.inputGrid is not None or self.inputGrid != NULL:
            qgsUtils.checkProjectionUnit(self.inputGrid)
              
        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Si grille non présente prendre l'emprise de la couche raster Viewshed
            if self.inputGrid is None or self.inputGrid == NULL:
                extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
                qgsTreatments.applyGetLayerExtent(self.inputViewshed, extent_zone, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = qgsUtils.loadVectorLayer(extent_zone)
                outputs[self.SLICED_RASTER_VIEWSHED] = self.inputViewshed # le raster n'est pas découpé
               
               # le raster bati est découpé pour avoir la même taille que le viewshed
                outputs[self.SLICED_RASTER_BATI] = qgsTreatments.applyClipRasterByExtent(self.inputRasterBati, outputs[self.EXTENT_ZONE], QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
                
                step+=2
                feedback.setCurrentStep(step)
                if feedback.isCanceled():
                    return {}
                    
             # Sinon prendre l'emprise de la grille
            else:
                # Découper le raster Viewshed selon une emprise (celle de la grille)
                outputs[self.SLICED_RASTER_VIEWSHED] = qgsTreatments.applyClipRasterByExtent(self.inputViewshed, self.inputGrid, QgsProcessing.TEMPORARY_OUTPUT, no_data=-999999999, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = self.inputGrid
                
                step+=1
                feedback.setCurrentStep(step)
                if feedback.isCanceled():
                    return {}
                
                # Découper le raster Bati selon une emprise (celle de la grille)
                outputs[self.SLICED_RASTER_BATI] = qgsTreatments.applyClipRasterByExtent(self.inputRasterBati, self.inputGrid, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
                
                step+=1
                feedback.setCurrentStep(step)
                if feedback.isCanceled():
                    return {}
        else:
            # Découper le raster Viewshed selon une emprise
            outputs[self.SLICED_RASTER_VIEWSHED] = qgsTreatments.applyClipRasterByExtent(self.inputViewshed, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, no_data=-999999999, context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] = self.inputExtent
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Découper le raster Bati selon une emprise
            outputs[self.SLICED_RASTER_BATI] =  qgsTreatments.applyClipRasterByExtent(self.inputRasterBati, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}

        if self.inputGrid is None or self.inputGrid == NULL:
            # Créer une grille
            # Ajoute +2 pour aligner le bon type de grille
            temp_path_grid = QgsProcessingUtils.generateTempFilename('temp_grid.gpkg')
            qgsTreatments.createGridLayer(outputs[self.EXTENT_ZONE], outputs[self.EXTENT_ZONE].crs(), parameters[self.DIM_GRID], temp_path_grid, gtype=parameters[self.TYPE_GRID]+2, context=context,feedback=feedback)
            outputs['GridTemp'] = qgsUtils.loadVectorLayer(temp_path_grid)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
        else:
            # Sinon on prend la grille donnée en paramètre
            step+=1
            outputs['GridTemp'] = self.inputGrid
            
        # grille indexée  
        qgsTreatments.createSpatialIndex(outputs['GridTemp'], context=context,feedback=feedback)

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Extraire la grille par localisation de l'emprise
        temp_path_grid_loc = QgsProcessingUtils.generateTempFilename('temp_grid_loc.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTemp'], outputs[self.EXTENT_ZONE],temp_path_grid_loc, context=context,feedback=feedback)
        outputs['GridTempExtract'] = qgsUtils.loadVectorLayer(temp_path_grid_loc)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
            
        # Calculatrice Raster enleve bati haut
        # Masque bati
        #Si hauteur > h_remplie  : 0 Sinon 1
        formula = '1*(logical_and(A<= '+str(parameters[self.MASK_HEIGHT])+', True))' #'1*(logical_and(A<= B, True))'
        outputs['RasterBatiFilterHeight'] = qgsTreatments.applyRasterCalcAB(outputs[self.SLICED_RASTER_BATI], None, QgsProcessing.TEMPORARY_OUTPUT, formula, nodata_val=None, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Remplir les cellules sans données
        outputs['FillCellsWithoutData'] = qgsTreatments.applyFillNoData(outputs['RasterBatiFilterHeight'], QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Mise à zéro du pixel sur bati supérieur à une certaine hauteur
        outputs['BatiWithHeightMask'] = qgsTreatments.applyRasterCalcAB(outputs[self.SLICED_RASTER_VIEWSHED], outputs['FillCellsWithoutData'], self.outputbSrcRaster, 'A*B',nodata_val=None, out_type=Qgis.Int16, context=context,feedback=feedback)
        self.results[self.OUTPUT_NB_SRC_RASTER] = outputs['BatiWithHeightMask']
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Statistiques de zone (moyenne)
        stats = [2,4] # Moyenne,Ecart-type
        self.results[self.OUTPUT_NB_SRC_VIS] = qgsTreatments.rasterZonalStats(outputs['GridTempExtract'], outputs['BatiWithHeightMask'], self.outputNbSrcVis, prefix='_',stats=stats, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        print(step)
        
        self.LAST_BOUNDS_VALUE = parameters[self.LAST_BOUNDS]
        
        return self.results

    def name(self):
        return 'AnalyseVisibilityLightSources'

    def displayName(self):
        return self.tr('Number sources of light visibility per grid')
        
    def tr(self, string):
        return QCoreApplication.translate(self.__class__.__name__, string)

    def group(self):
        return  self.tr('Light Pollution Indicators')

    def groupId(self):
        return 'lightPollutionIndicators'

    def createInstance(self):
        return AnalyseVisibilityLightSources()
        
    def postProcessAlgorithm(self,context,feedback):
        out_layer = QgsProcessingUtils.mapLayerFromString(self.results[self.OUTPUT_NB_SRC_VIS],context)
        if not out_layer:
            raise QgsProcessingException("No layer found for " + str(self.results[self.OUTPUT_NB_SRC_VIS]))
        
        # Applique la symbologie par défault
        # styles.setCustomClassesInd_Pol_Graduate(out_layer, self.FIELD_STYLE, self.CLASS_BOUNDS_NB_SRC) # affecte une couleur par valeur
        # styles.setRdYlGnGraduatedStyle2(out_layer, self.FIELD_STYLE)
        
        bounds = styles.getQuantileBounds(out_layer, self.FIELD_STYLE, lastBounds=self.LAST_BOUNDS_VALUE)
        styles.setCustomClassesInd_Pol_Graduate(out_layer, self.FIELD_STYLE, bounds)
        
        return self.results

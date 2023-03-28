"""
Model exported as python.
Name : Analyse niveau de radiance par maille
Group : ASE
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
from qgis.core import QgsProcessingParameterFeatureSource
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles

class StatisticsRadianceGrid(QgsProcessingAlgorithm):
    
    ALG_NAME = 'StatisticsRadianceGrid'
    
    RASTER_INPUT = 'ImageJILINradianceRGB'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    DIM_GRID = 'GridDiameter'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    GRID_LAYER_INPUT = 'GridLayerInput'
    OUTPUT_STAT = 'OutputStat'
    
    # MAJORITY_FIELD = "_majority"
 
    SLICED_RASTER = 'SlicedRaster'
    
    IND_FIELD_POL = 'indice_pol'
    CLASS_BOUNDS_IND_POL = [0,1,2,3,4,5]
    results = {}
    
    def initAlgorithm(self, config=None):
        # Utiliser QgsProcessingParameterFeatureSource si on veut uniquement les entitées selectionnées : mais la sélection ne marche pas
        self.addParameter(QgsProcessingParameterVectorLayer(self.EXTENT_ZONE, self.tr('Extent zone'), optional=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Image JILIN radiance RGB'),defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer(self.GRID_LAYER_INPUT, self.tr('Grid Layer'), optional=True, defaultValue=None))
        
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID, self.tr('Grid diameter (meter) if no grid layer'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid if no grid layer'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, usesStaticStrings=False, defaultValue=2))
        
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
        self.inputGrid = self.parameterAsVectorLayer(parameters, self.GRID_LAYER_INPUT, context)
        self.outputStat = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT,context)
       
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(19, model_feedback)
        
        outputs = {}
        
        self.parseParams(parameters,context)
        
        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Si grille non présente prendre l'emprise de la couche raster
            if self.inputGrid is None or self.inputGrid == NULL:
                extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
                outputs[self.EXTENT_ZONE] = qgsTreatments.applyGetLayerExtent(self.inputRaster, extent_zone, context=context,feedback=feedback)
                outputs[self.SLICED_RASTER] = self.inputRaster # le raster n'est pas découpé
            # Sinon prendre l'emprise de la grille
            else:
                # Découper un raster selon une emprise (celle de la grille)
                outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputGrid, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = self.inputGrid
                
        else:
            # Découper un raster selon une emprise
            outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] = self.inputExtent

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        
        if self.inputGrid is None or self.inputGrid == NULL:
            # Créer une grille
            # Ajoute +2 pour aligner le bon type de grille
            temp_path_grid = QgsProcessingUtils.generateTempFilename('temp_grid.gpkg')
            qgsTreatments.createGridLayer(outputs[self.EXTENT_ZONE], outputs[self.EXTENT_ZONE], parameters[self.DIM_GRID], temp_path_grid, gtype=parameters[self.TYPE_GRID]+2, context=context,feedback=feedback)
            outputs['GridTemp'] = qgsUtils.loadVectorLayer(temp_path_grid)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
        else:
        # Sinon on prend la grille donnée en paramètre
            outputs['GridTemp'] = self.inputGrid
        
        # Extraire les grilles par localisation de l'emprise
        temp_path_grid_loc = QgsProcessingUtils.generateTempFilename('temp_grid_loc.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTemp'], outputs[self.EXTENT_ZONE],temp_path_grid_loc, context=context,feedback=feedback)
        outputs['GridTempExtract'] = qgsUtils.loadVectorLayer(temp_path_grid_loc)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}
            
        # grille indexée
        qgsTreatments.createSpatialIndex(outputs['GridTempExtract'], context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        
        if feedback.isCanceled():
            return {}
        
        # ########################################################################## PRETRAITEMENTS A SORTIR ##########################################################################
        
        # # Statistiques de zone pour les 3 bandes afin de récupérer les pixels majoritaires
        # majorityBand1 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
        
        # majorityBand2 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.GREEN_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
        
        # majorityBand3 = qgsTreatments.getMajorityValue(outputs[self.EXTENT_ZONE], outputs[self.SLICED_RASTER], parameters[self.BLUE_BAND_INPUT],self.MAJORITY_FIELD, context, feedback)
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}

        # # Calculatrice Raster masque pour enlever les zones non éclairées
        # # Si les pixels < majortité+1 alors 0, sinon 1 
        # # Ici la condition indique l'inverse : pour mettre les pixels à 1, il faut qu'au moins 1 des 3 soit > majorité
        # # Pour enlver le bruit qui correspond à des couleurs uniques ou seule une bande a une valeur forte, on vérifie qu'au moins 2 bandes aient une valeur > majortité
        # # #(A > maj1 AND B > maj2) OR (A > maj1 AND C > maj3) OR (B > maj2 AND C > maj3)
        # # 'FORMULA': '1*logical_or(logical_or(logical_and((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')),logical_and((A>'+str(majorityBand1)+'), (C>'+str(majorityBand3)+'))),logical_and((B>'+str(majorityBand2)+'), (C>'+str(majorityBand3)+')))',

        # formula = '1*logical_or(logical_or((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')), (C >'+str(majorityBand3)+'))'
        # outputs['CalculRasterMask'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],parameters[self.GREEN_BAND_INPUT], parameters[self.BLUE_BAND_INPUT],QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
        
        # # Calculatrice Raster B1 avec masque
        # formula = 'A*B'
        # outputs['CalculRasterB1'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.RED_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
            
        # # Calculatrice Raster B2 avec masque
        # formula = 'A*B'
        # outputs['CalculRasterB2'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.GREEN_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
            
        # # Calculatrice Raster B3 avec masque
        # formula = 'A*B'
        # outputs['CalculRasterB3'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.BLUE_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}    
        
        # ##############################################################################################################################################################################################################################
        
        
        # Calculatrice Raster Radiance totale
        formula = 'A*0.2989+B*0.5870+C*0.1140'
        outputs['CalculRasterTotalRadiance'] = qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], outputs[self.SLICED_RASTER], parameters[self.RED_BAND_INPUT],parameters[self.GREEN_BAND_INPUT], parameters[self.BLUE_BAND_INPUT],QgsProcessing.TEMPORARY_OUTPUT, formula, context=context,feedback=feedback)
                
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Calculatrice Raster Segmentation
        # Si rad totale > mediane+1 : 1 sinon 0
        formula = '1*(logical_or(A>(median(A)+1) , False))'
        outputs['CalculRasterSegmentation'] = qgsTreatments.applyRasterCalcABC(outputs['CalculRasterTotalRadiance'], None, None, 1, None, None, QgsProcessing.TEMPORARY_OUTPUT, formula, context=context,feedback=feedback)
         
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Polygoniser zone éclairée
        outputs['PolygoniseLightZone'] = qgsTreatments.applyPolygonize(outputs['CalculRasterSegmentation'], 'DN', QgsProcessing.TEMPORARY_OUTPUT, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire zone éclairée
        temp_path_extract_light = QgsProcessingUtils.generateTempFilename('temp_extract_light.gpkg')
        qgsTreatments.applyExtractByAttribute(outputs['PolygoniseLightZone'], 'DN', temp_path_extract_light, context=context, feedback=feedback)
        outputs['ExtractLightZone'] = qgsUtils.loadVectorLayer(temp_path_extract_light)
        # outputs['ExtractLightZone'] = qgsTreatments.applyExtractByAttribute(outputs['PolygoniseLightZone'], 'DN', QgsProcessing.TEMPORARY_OUTPUT, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Réparer les géométries
        light_zone_fixed = QgsProcessingUtils.generateTempFilename('light_zone_fixed.gpkg')
        qgsTreatments.fixGeometries(outputs['ExtractLightZone'],light_zone_fixed,context=context,feedback=feedback)
        outputs['ExtractLightZone'] = qgsUtils.loadVectorLayer(light_zone_fixed)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # zones éclairées indexées
        qgsTreatments.createSpatialIndex(outputs['ExtractLightZone'], context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire maille éclairée
        temp_path_light_grid = QgsProcessingUtils.generateTempFilename('temp_path_light_grid.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTempExtract'], outputs['ExtractLightZone'],temp_path_light_grid, context=context,feedback=feedback)
        outputs['ExtractLightGrid'] = qgsUtils.loadVectorLayer(temp_path_light_grid)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande rouge
        zonal_stats_r = QgsProcessingUtils.generateTempFilename('zonal_stats_r.gpkg')
        qgsTreatments.rasterZonalStats(outputs['ExtractLightGrid'], outputs[self.SLICED_RASTER],zonal_stats_r, prefix='R_', band=parameters[self.RED_BAND_INPUT], context=context,feedback=feedback)
        outputs['StatisticsRedBand'] = qgsUtils.loadVectorLayer(zonal_stats_r)
        step+=1               
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande verte
        zonal_stats_g = QgsProcessingUtils.generateTempFilename('zonal_stats_g.gpkg')
        qgsTreatments.rasterZonalStats(outputs['StatisticsRedBand'], outputs[self.SLICED_RASTER],zonal_stats_g, prefix='V_', band=parameters[self.GREEN_BAND_INPUT], context=context,feedback=feedback)
        outputs['StatisticsGreenBand'] = qgsUtils.loadVectorLayer(zonal_stats_g)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Statistiques de zone bande bleu
        zonal_stats_b = QgsProcessingUtils.generateTempFilename('zonal_stats_b.gpkg')
        qgsTreatments.rasterZonalStats(outputs['StatisticsGreenBand'], outputs[self.SLICED_RASTER],zonal_stats_b, prefix='B_', band=parameters[self.BLUE_BAND_INPUT], context=context,feedback=feedback)
        outputs['StatisticsBlueBand'] = qgsUtils.loadVectorLayer(zonal_stats_b)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Statistiques de zone radiance totale
        zonal_stats_tot = QgsProcessingUtils.generateTempFilename('zonal_stats_tot.gpkg')
        qgsTreatments.rasterZonalStats(outputs['StatisticsBlueBand'], outputs['CalculRasterTotalRadiance'],zonal_stats_tot, prefix='tot_', context=context,feedback=feedback)
        outputs['StatisticsZoneTotalRadiance'] = qgsUtils.loadVectorLayer(zonal_stats_tot)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # # TODO Ajout calcul rad_tot/m² ou hectare :
        # # Création champs tot_sum/surface et calcul des indicateurs avec ce champ
        # fieldLength = 10
        # fieldPrecision = 4
        # fieldType = 0 # Flottant
        # formula = '"tot_sum"/$area'
        # temp_path_radiance_surface = QgsProcessingUtils.generateTempFilename('temp_path_radiance_surface.gpkg')
        # qgsTreatments.applyFieldCalculator(outputs['StatisticsZoneTotalRadiance'], 'radiance_surface', temp_path_radiance_surface, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        # outputs['StatisticsZoneTotalRadiance'] = qgsUtils.loadVectorLayer(temp_path_radiance_surface)
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
        
        # Calculatrice de champ indice radiance
        fieldLength = 6
        fieldPrecision = 0
        fieldType = 1 # Entier
        field_quartile = 'tot_mean' #'radiance_surface'
        formula = 'with_variable(\'percentile\',array_find(array_agg("'+field_quartile+'",order_by:="'+field_quartile+'"),"'+field_quartile+'") / array_length(array_agg("'+field_quartile+'")), CASE WHEN @percentile < 0.2 THEN 1 WHEN @percentile < 0.4 THEN 2 WHEN @percentile < 0.6 THEN 3 WHEN @percentile < 0.8 THEN 4 WHEN @percentile <= 1 THEN 5 ELSE 0 END)'
        temp_path_ind_radiance = QgsProcessingUtils.generateTempFilename('temp_path_ind_radiance.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['StatisticsZoneTotalRadiance'], self.IND_FIELD_POL, temp_path_ind_radiance, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        outputs['CalculFieldIndiceRadiance'] = qgsUtils.loadVectorLayer(temp_path_ind_radiance)
    
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Extraire par maille non éclairée (utilisé ensuite pour fusionner avec mailles éclairées)
        # est disjoint
        temp_path_dark_grid = QgsProcessingUtils.generateTempFilename('temp_path_dark_grid.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTempExtract'], outputs['ExtractLightZone'],temp_path_dark_grid, predicate=[2], context=context,feedback=feedback)
        outputs['ExtractDarkGrid'] = qgsUtils.loadVectorLayer(temp_path_dark_grid)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ indice radiance null sur les mailles non éclairées
        fieldLength = 6
        fieldPrecision = 0
        fieldType = 1 # Entier
        formula = '0'
        temp_path_radiance_null = QgsProcessingUtils.generateTempFilename('temp_path_radiance_null.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['ExtractDarkGrid'], self.IND_FIELD_POL, temp_path_radiance_null, formula, fieldLength, fieldPrecision, fieldType, context=context,feedback=feedback)
        outputs['CalculFieldIndiceRadianceNull'] = qgsUtils.loadVectorLayer(temp_path_radiance_null)
      
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Fusionner des couches vecteur (grilles avec radiance et grilles sans radiance)
        layersToMerge = [outputs['CalculFieldIndiceRadiance'],outputs['CalculFieldIndiceRadianceNull']]
        self.results[self.OUTPUT_STAT] = qgsTreatments.mergeVectorLayers(layersToMerge,outputs['CalculFieldIndiceRadiance'],self.outputStat, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        print(step)
        
        return self.results

    def name(self):
        return 'StatisticsRadianceGrid'

    def displayName(self):
        return self.tr('Statistics of radiance per grid')
        
    # def group(self):
        # return 'ASE'

    # def groupId(self):
        # return 'ASE'

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
        styles.setCustomClassesInd_Pol_Category(out_layer, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)

        return self.results

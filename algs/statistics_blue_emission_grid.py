"""
Model exported as python.
Name : Analyse blue emission per grid
Group : ASE
With QGIS : 32215
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsUnitTypes
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
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingUtils
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles



class StatisticsBlueEmissionGrid(QgsProcessingAlgorithm):
    
    ALG_NAME = 'StatisticsBlueEmissionGrid'

    RASTER_INPUT = 'ImageSat'
    RED_BAND_INPUT = 'RedBandInput'
    GREEN_BAND_INPUT = 'GreenBandInput'
    BLUE_BAND_INPUT = 'BlueBandInput'
    DIM_GRID_CALC = 'DiameterGridCalcul'
    # DIM_GRID_RES = 'DiameterGridResultat'
    TYPE_GRID = 'TypeOfGrid'
    EXTENT_ZONE = 'ExtentZone'
    GRID_LAYER_INPUT = 'GridLayerInput'
    OUTPUT_STAT_CALC = 'OutputStatCalcul'
    # OUTPUT_STAT_RES = 'OutputStatResult'
    
    MAJORITY_FIELD = "_majority"

    SLICED_RASTER = 'SlicedRaster'
    
    IND_FIELD_POL = 'indice_pol'
    CLASS_BOUNDS_IND_POL = [0,1,2,3,4,5]

    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Satellite Image RGB'),defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSource(self.GRID_LAYER_INPUT, self.tr('Grid Layer'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID_CALC, self.tr('Grid diameter (min 150 meters) if no grid layer'), type=QgsProcessingParameterNumber.Double, defaultValue=150))
        # self.addParameter(QgsProcessingParameterNumber(self.DIM_GRID_RES, self.tr('Diameter grid result (meter)'), type=QgsProcessingParameterNumber.Double, defaultValue=50))
        self.addParameter(QgsProcessingParameterEnum(self.TYPE_GRID, self.tr('Type of grid if no grid layer'), options=['Rectangle','Diamond','Hexagon'], allowMultiple=False, defaultValue=2))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT_CALC, self.tr('statistics blue emission'), type=QgsProcessing.TypeVectorAnyGeometry))
        # self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_STAT_RES, self.tr('statistics blue emission 50m'), type=QgsProcessing.TypeVectorAnyGeometry))
                
        param = QgsProcessingParameterNumber(self.RED_BAND_INPUT, self.tr('Index of the red band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=1)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.GREEN_BAND_INPUT, self.tr('Index of the green band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=2)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterNumber(self.BLUE_BAND_INPUT, self.tr('Index of the blue band'), type=QgsProcessingParameterNumber.Integer, minValue=1, maxValue=4, defaultValue=3)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
    
    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1] 
        self.inputRaster = self.parameterAsRasterLayer(parameters, self.RASTER_INPUT, context)
        self.inputGrid = qgsTreatments.parameterAsSourceLayer(self, parameters,self.GRID_LAYER_INPUT,context,feedback=feedback)[1] 
        self.outputStatCalc = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT_CALC,context)       
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(8, model_feedback)

        outputs = {}
        
        self.parseParams(parameters, context, feedback)
        
        # Test projection des input sont bien en unité métrique
        if self.inputExtent is not None or self.inputExtent != NULL:
            qgsUtils.checkProjectionUnit(self.inputExtent)
        qgsUtils.checkProjectionUnit(self.inputRaster)
        if self.inputGrid is not None or self.inputGrid != NULL:
            qgsUtils.checkProjectionUnit(self.inputGrid)
        
        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            # Si grille non présente prendre l'emprise de la couche raster
            # Extraire l'emprise de la couche raster
            if self.inputGrid is None or self.inputGrid == NULL:
                extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
                qgsTreatments.applyGetLayerExtent(self.inputRaster, extent_zone, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = qgsUtils.loadVectorLayer(extent_zone)
                outputs[self.SLICED_RASTER] = self.inputRaster # le raster n'est pas découpé
            # Sinon prendre l'emprise de la grille
            else:
                # Découper un raster selon une emprise (celle de la grille)
                outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputGrid, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
                outputs[self.EXTENT_ZONE] = self.inputGrid
        else:
            # Découper un raster selon l'emprise
            outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] = self.inputExtent
            
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # if parameters[self.DIM_GRID_CALC] != parameters[self.DIM_GRID_RES]: # uniquement sur les 2 grilles sont de taille différente
            # self.outputStatRes = self.parameterAsOutputLayer(parameters,self.OUTPUT_STAT_RES,context) # TODO mettre aillieurs ?
            # # Créer une grille de résultat
            # alg_params = {
                # 'CRS': outputs[self.EXTENT_ZONE],
                # 'EXTENT': outputs[self.EXTENT_ZONE],
                # 'HOVERLAY': 0,
                # 'HSPACING': parameters[self.DIM_GRID_RES],
                # 'TYPE': parameters[self.TYPE_GRID]+2,  # Ajoute +2 pour aligner le bon type de grille
                # 'VOVERLAY': 0,
                # 'VSPACING': parameters[self.DIM_GRID_RES],
                # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            # }
            # outputs['GridTempRes'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            # step+=1
            # feedback.setCurrentStep(step)
            # if feedback.isCanceled():
                # return {}
                
            # # Extraire les grilles resultat par localisation de l'emprise
            # alg_params = {
                # 'INPUT': outputs['GridTempRes']['OUTPUT'],
                # 'INTERSECT': outputs[self.EXTENT_ZONE],
                # 'PREDICATE': [0],  # intersecte
                # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            # }
            # outputs['GridTempResExtract'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            # step+=1
            # feedback.setCurrentStep(step)
            # if feedback.isCanceled():
                # return {}

            # # grille résultat indexée
            # alg_params = {
                # 'INPUT': outputs['GridTempResExtract']['OUTPUT']
            # }
            # outputs['GridTempResIndex'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            # step+=1
            # feedback.setCurrentStep(step)
            # if feedback.isCanceled():
                # return {}
        
        if self.inputGrid is None or self.inputGrid == NULL:
            # Créer une grille de calcul
            temp_path_grid = QgsProcessingUtils.generateTempFilename('temp_grid.gpkg')
            qgsTreatments.createGridLayer(outputs[self.EXTENT_ZONE], outputs[self.EXTENT_ZONE].crs(), parameters[self.DIM_GRID_CALC], temp_path_grid, gtype=parameters[self.TYPE_GRID]+2, context=context,feedback=feedback)
            outputs['GridTempCalc'] = qgsUtils.loadVectorLayer(temp_path_grid)
            
        else:
        # Sinon on prend la grille donnée en paramètre
            outputs['GridTempCalc'] = self.inputGrid
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # grille de calcul indexée
        qgsTreatments.createSpatialIndex(outputs['GridTempCalc'], context=context,feedback=feedback)

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Extraire les grilles de calcul par localisation de l'emprise
        temp_path_grid_loc = QgsProcessingUtils.generateTempFilename('temp_grid_loc.gpkg')
        qgsTreatments.extractByLoc(outputs['GridTempCalc'], outputs[self.EXTENT_ZONE],temp_path_grid_loc, context=context,feedback=feedback)
        outputs['GridTempCalcExtract'] = qgsUtils.loadVectorLayer(temp_path_grid_loc)
        
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
        # # Ici la condition indique l'inverse : pour mettre les pixels à 1, il faut qu'au moins 1 des bandes soit > majorité
        # # Pour enlver le bruit qui correspond à des couleurs uniques ou seule une bande a une valeur forte, on vérifie qu'au moins 2 bandes aient une valeur > majortité
        # # 'FORMULA': '1*logical_or(logical_or(logical_and((A>'+str(majorityBand1)+'), (B>'+str(majorityBand2)+')),logical_and((A>'+str(majorityBand1)+'), (C>'+str(majorityBand3)+'))),logical_and((B>'+str(majorityBand2)+'), (C>'+str(majorityBand3)+')))',
        # #(A > maj1 AND B > maj2) OR (A > maj1 AND C > maj3) OR (B > maj2 AND C > maj3)
        
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

        # # Calculatrice Raster B3 avec masque
        # formula = 'A*B'
        # outputs['CalculRasterB3'] =  qgsTreatments.applyRasterCalcABC(outputs[self.SLICED_RASTER], outputs['CalculRasterMask'], None, parameters[self.BLUE_BAND_INPUT],1, None, QgsProcessing.TEMPORARY_OUTPUT, formula,out_type=Qgis.UInt16, context=context,feedback=feedback)
        
        # step+=1       
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}
        ##############################################################################################################################################################################################################################
        
        # Statistiques de zone bande rouge
        stats = [0,1,2,3,4] # Count Somme,Moyenne, Médiane, Ecart-type
        zonal_stats_r = QgsProcessingUtils.generateTempFilename('zonal_stats_r.gpkg')
        qgsTreatments.rasterZonalStats(outputs['GridTempCalcExtract'], outputs[self.SLICED_RASTER],zonal_stats_r, prefix='R_', band=parameters[self.RED_BAND_INPUT],stats=stats, context=context,feedback=feedback)
        outputs['StatisticsRedBand'] = qgsUtils.loadVectorLayer(zonal_stats_r)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Statistiques de zone bande bleu     
        zonal_stats_b = QgsProcessingUtils.generateTempFilename('zonal_stats_b.gpkg')
        qgsTreatments.rasterZonalStats(outputs['StatisticsRedBand'], outputs[self.SLICED_RASTER],zonal_stats_b, prefix='B_', band=parameters[self.BLUE_BAND_INPUT],stats=stats, context=context,feedback=feedback)
        outputs['StatisticsBlueBand'] = qgsUtils.loadVectorLayer(zonal_stats_b)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Calcul champ R/B_mean
        # NULL si R_mean ou B_mean = 0
        formula = 'CASE\r\n\tWHEN "R_mean" = 0 or "B_mean" = 0 THEN NULL\r\n\tELSE "R_mean"/"B_mean"\r\nEND' # TEST INDICE NORMALISE B-R/B+R : ("B_mean"-"R_mean")/("B_mean"+"R_mean")
        temp_path_RB = QgsProcessingUtils.generateTempFilename('temp_path_RB.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['StatisticsBlueBand'],'R/B_mean', temp_path_RB, formula, 10, 4, 0, context=context,feedback=feedback)
        outputs['CalculFieldRb_mean'] = qgsUtils.loadVectorLayer(temp_path_RB)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # # Calcul champ R/B_Q3
        # # NULL si R_mean ou B_mean = 0
        # # TODO : trouver comment récupérer le q3 du raster
        # alg_params = {
            # 'FIELD_LENGTH': 10,
            # 'FIELD_NAME': 'R/B_Q3',
            # 'FIELD_PRECISION': 4,
            # 'FIELD_TYPE': 0,  # Flottant
            # 'FORMULA': 'CASE\r\n\tWHEN "R_stdev" = 0 or "B_stdev" = 0 THEN NULL\r\n\tELSE "R_stdev"/"B_stdev"\r\nEND',
            # 'INPUT': outputs['CalculFieldRb_mean']['OUTPUT'],
            # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        # }
        # outputs['CalculFieldRb_q3'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # step+=1
        # feedback.setCurrentStep(step)
        # if feedback.isCanceled():
            # return {}

        # Calculatrice de champ indice bleu pour la couche de calcul
        # quantiles inversés
        # Filtre R/B_mean non NULL
        outputs['CalculFieldRb_mean'].setSubsetString('"R/B_mean" is not NULL')
        formula = 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("R/B_mean",order_by:="R/B_mean"),"R/B_mean") / array_length(array_agg("R/B_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 5\r\n    WHEN @percentile < 0.4 THEN 4\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 2\r\n    WHEN @percentile <= 1 THEN 1\r\n    ELSE 0\r\n    END\r\n)'
        temp_path_RBmeanNotNull = QgsProcessingUtils.generateTempFilename('temp_path_RBmeanNotNull.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['CalculFieldRb_mean'],self.IND_FIELD_POL, temp_path_RBmeanNotNull, formula, 6, 0, 1, context=context,feedback=feedback)
        
        # Filtre R/B_mean NULL
        outputs['CalculFieldRb_mean'].setSubsetString('"R/B_mean" is NULL')
        formula = '0'
        temp_path_RBmeanNull = QgsProcessingUtils.generateTempFilename('temp_path_RBmeanNull.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['CalculFieldRb_mean'],self.IND_FIELD_POL, temp_path_RBmeanNull, formula, 6, 0, 1, context=context,feedback=feedback)
        
        # Fusion R/B_mean NULL et non NULL
        layersToMerge = [temp_path_RBmeanNotNull,temp_path_RBmeanNull]
        self.results[self.OUTPUT_STAT_CALC] = qgsTreatments.mergeVectorLayers(layersToMerge,outputs['CalculFieldRb_mean'],self.outputStatCalc, context=context, feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # if parameters[self.DIM_GRID_CALC] != parameters[self.DIM_GRID_RES]: # uniquement si les 2 grilles sont de taille différente
            # # Joindre les attributs par localisation (résumé)
            # # Intersection entre les grilles de calcul et de résultat
            # alg_params = {
                # 'DISCARD_NONMATCHING': False,
                # 'INPUT': outputs['GridTempResIndex']['OUTPUT'],
                # 'JOIN': outputs['CalculFieldRb_mean']['OUTPUT'],#outputs['CalculFieldRb_q3']['OUTPUT'],
                # 'JOIN_FIELDS': [''],
                # 'PREDICATE': [0],  # intersecte
                # 'SUMMARIES': [6],  # mean
                # 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            # }
            # outputs['JoinFieldsLocalisationCalculResult'] = processing.run('qgis:joinbylocationsummary', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            # step+=1
            # feedback.setCurrentStep(step)
            # if feedback.isCanceled():
                # return {}
        
            # # Calculatrice de champ indice bleu pour la couche de résultat
            # # quantiles inversés
            # alg_params = {
                # 'FIELD_LENGTH': 6,
                # 'FIELD_NAME': self.IND_FIELD_POL,
                # 'FIELD_PRECISION': 0,
                # 'FIELD_TYPE': 1,  # Entier
                # 'FORMULA': 'with_variable(\r\n\'percentile\',\r\narray_find(array_agg("R/B_mean_mean",order_by:="R/B_mean_mean"),"R/B_mean_mean") / array_length(array_agg("R/B_mean_mean")),\r\n    CASE\r\n    WHEN @percentile < 0.2 THEN 5\r\n    WHEN @percentile < 0.4 THEN 4\r\n    WHEN @percentile < 0.6 THEN 3\r\n    WHEN @percentile < 0.8 THEN 2\r\n    WHEN @percentile <= 1 THEN 1\r\n    ELSE 0\r\n    END\r\n)',
                # 'INPUT': outputs['JoinFieldsLocalisationCalculResult']['OUTPUT'],
                # 'OUTPUT': self.outputStatRes
            # }
            # outputs['CalculFieldIndicatorRes'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            # self.results[self.OUTPUT_STAT_RES] = outputs['CalculFieldIndicatorRes']['OUTPUT']
            
            # step+=1
            # feedback.setCurrentStep(step)
            # if feedback.isCanceled():
                # return {}

        print(step)

        return self.results
        

    def name(self):
        return 'StatisticsBlueEmissionGrid'

    def displayName(self):
        return self.tr('Statistics of blue emission per grid')

    def group(self):
        return self.tr('Light Pollution Indicators')

    def groupId(self):
        return 'lightPollutionIndicators'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate(self.__class__.__name__, string)

    def createInstance(self):
        return StatisticsBlueEmissionGrid()

    def postProcessAlgorithm(self,context,feedback):
        out_layer_calc = QgsProcessingUtils.mapLayerFromString(self.results[self.OUTPUT_STAT_CALC],context)
        if not out_layer_calc:
            raise QgsProcessingException("No layer found for " + str(self.results[self.OUTPUT_STAT_CALC]))
        # Applique la symbologie par défault pour couche de calcul
        styles.setCustomClassesInd_Pol_Category(out_layer_calc, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)

        # if self.OUTPUT_STAT_RES in self.results:
            # out_layer_res = QgsProcessingUtils.mapLayerFromString(self.results[self.OUTPUT_STAT_RES],context)
            # if not out_layer_res:
                # raise QgsProcessingException("No layer found for " + str(self.results[self.OUTPUT_STAT_RES]))
            # # Applique la symbologie par défault de résultat
            # styles.setCustomClassesInd_Pol_Category(out_layer_res, self.IND_FIELD_POL, self.CLASS_BOUNDS_IND_POL)

        return self.results

"""
Model exported as python.
Name : MNS
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
from qgis.core import QgsProcessingParameterFeatureSource
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
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_MNT_INPUT, self.tr('MNT'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.BUFFER_RADIUS, 'Radius of analysis for visibility (buffer of extent), meters', type=QgsProcessingParameterNumber.Double, defaultValue=500))
        
        self.addParameter(QgsProcessingParameterFeatureSource(self.BATI_INPUT, self.tr('Buildings (BD TOPO)'), types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterField(self.HEIGHT_FIELD_BATI, self.tr('Height Buildings field'), type=QgsProcessingParameterField.Any, parentLayerParameterName=self.BATI_INPUT, allowMultiple=False, defaultValue='HAUTEUR'))
        
        self.addParameter(QgsProcessingParameterFeatureSource(self.VEGETATION_INPUT, self.tr('Vegetation (BD TOPO)'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterField(self.HEIGHT_FIELD_VEGETATION, self.tr('Height Vegetation field'), optional=True, type=QgsProcessingParameterField.Any, parentLayerParameterName=self.VEGETATION_INPUT, allowMultiple=False, defaultValue='HAUTEUR'))
        self.addParameter(QgsProcessingParameterNumber(self.DEFAULT_HEIGHT_VEGETATION, 'Height Vegetation by default if no field', optional=True, type=QgsProcessingParameterNumber.Double, defaultValue=6))
        
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_MNS, self.tr('MNS'), createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_BATI, self.tr('Raster bati vegetation'), createByDefault=True, defaultValue=None))
        
        # self.addParameter(QgsProcessingParameterVectorDestination('VegetationWithoutBati', 'vegetation', type=QgsProcessing.TypeVectorAnyGeometry,createByDefault=True, defaultValue=None)) # POUR TESTER

    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1] 
        self.inputRasterMNT = self.parameterAsRasterLayer(parameters, self.RASTER_MNT_INPUT, context)
        self.inputBati = qgsTreatments.parameterAsSourceLayer(self, parameters,self.BATI_INPUT,context,feedback=feedback)[1] 
        self.inputVegetation = qgsTreatments.parameterAsSourceLayer(self, parameters,self.VEGETATION_INPUT,context,feedback=feedback)[1] 
        self.outputRasterMNS = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_MNS,context)
        self.outputRasterBati = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_BATI,context)
        
        # self.outputVegetation = self.parameterAsOutputLayer(parameters,'VegetationWithoutBati', context)
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(16, model_feedback)
       
        outputs = {}
        
        self.parseParams(parameters, context, feedback)
        
        # Extraire l'emprise de la couche
        # Si emprise non présente, on prend celle du MNS
        if self.inputExtent is None or self.inputExtent == NULL:
            # Mise à 1 à tous les pixels
            outputs['RasterMonoValue'] = qgsTreatments.applyRasterCalcAB(self.inputRasterMNT, None, QgsProcessing.TEMPORARY_OUTPUT,'1', nodata_val=None,out_type=Qgis.Int16, context=context,feedback=feedback)
            # Raster vers vecteur pour avoir l'emprise présise
            outputs[self.EXTENT_ZONE] = qgsTreatments.applyPolygonize(outputs['RasterMonoValue'], 'DN', QgsProcessing.TEMPORARY_OUTPUT, context=context, feedback=feedback)
            # extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
            # outputs[self.EXTENT_ZONE] = qgsTreatments.applyGetLayerExtent(self.inputRasterMNT, extent_zone, context=context,feedback=feedback)            
        else:
            # Tampon
            expr = parameters[self.BUFFER_RADIUS]
            temp_path_buf = QgsProcessingUtils.generateTempFilename('temp_path_buf.gpkg')
            qgsTreatments.applyBufferFromExpr(self.inputExtent,expr, temp_path_buf,context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] =  qgsUtils.loadVectorLayer(temp_path_buf)
            
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        # Découper le raster selon une emprise
        outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRasterMNT, outputs[self.EXTENT_ZONE], self.outputRasterMNS,data_type=6, context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire l'emprise de la couche raster, nécessaire pour rasterister ensuite
        temp_path_raster_extent = QgsProcessingUtils.generateTempFilename('temp_path_raster_extent.gpkg')
        qgsTreatments.applyGetLayerExtent(outputs[self.SLICED_RASTER], temp_path_raster_extent, context=context,feedback=feedback)
        outputs['RasterExtent'] = qgsUtils.loadVectorLayer(temp_path_raster_extent)
        
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Extraire par localisation le bati
        # Filtre sur l'emprise
        temp_path_loc_bati = QgsProcessingUtils.generateTempFilename('temp_path_loc_bati.gpkg')
        qgsTreatments.extractByLoc(self.inputBati, outputs[self.EXTENT_ZONE],temp_path_loc_bati, predicate=[6], context=context,feedback=feedback) # predicate=[6] # est à l'intérieur
        outputs['LocalisationBatiExtraction'] = qgsUtils.loadVectorLayer(temp_path_loc_bati)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ hauteur mediane
        formula = 'median("'+parameters[self.HEIGHT_FIELD_BATI]+'")'
        temp_path_bati_median = QgsProcessingUtils.generateTempFilename('temp_path_bati_median.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['LocalisationBatiExtraction'],'median_h',temp_path_bati_median, formula, 6, 2, 0, context=context,feedback=feedback)
        outputs['CalculFieldHeightBatiMedian'] = qgsUtils.loadVectorLayer(temp_path_bati_median)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Calculatrice de champ remplacement hauteur NULL par mediane
        formula = 'CASE\r\n\tWHEN  '+""+parameters[self.HEIGHT_FIELD_BATI]+""+' IS NULL THEN "median_h"\r\n\tELSE '+""+parameters[self.HEIGHT_FIELD_BATI]+""+'\r\nEND\r\n'
        temp_path_bati_null = QgsProcessingUtils.generateTempFilename('temp_path_bati_null.gpkg')
        qgsTreatments.applyFieldCalculator(outputs['CalculFieldHeightBatiMedian'], parameters[self.HEIGHT_FIELD_BATI],temp_path_bati_null, formula, 6, 2, 0, context=context,feedback=feedback)
        outputs['CalculFieldHeightBatiReplaceNullByMedian'] = qgsUtils.loadVectorLayer(temp_path_bati_null)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Si la végétation est présente
        if self.inputVegetation is not None and self.inputVegetation != NULL and parameters[self.DEFAULT_HEIGHT_VEGETATION] is not None and parameters[self.DEFAULT_HEIGHT_VEGETATION] != NULL:
            if parameters[self.HEIGHT_FIELD_VEGETATION] != "" and parameters[self.HEIGHT_FIELD_VEGETATION] is not None and parameters[self.HEIGHT_FIELD_VEGETATION] != NULL:
                # Extraire par attribut en enlevant les polygones sans hauteur
                temp_path_veg_height = QgsProcessingUtils.generateTempFilename('temp_path_veg_height.gpkg')
                # 'OPERATOR': 9,  # n'est pas null
                qgsTreatments.applyExtractByAttribute(self.inputVegetation, parameters[self.HEIGHT_FIELD_VEGETATION], temp_path_veg_height, operator = 9, value='', context=context, feedback=feedback)
                outputs['FilterVegetationWithHeight'] = qgsUtils.loadVectorLayer(temp_path_veg_height)
            else :
                outputs['FilterVegetationWithHeight'] = self.inputVegetation
                
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Extraction en fonction de l'emprise
            temp_path_loc_veg = QgsProcessingUtils.generateTempFilename('temp_path_loc_veg.gpkg')
            qgsTreatments.extractByLoc(outputs['FilterVegetationWithHeight'], outputs[self.EXTENT_ZONE],temp_path_loc_veg, predicate=[6], context=context,feedback=feedback)
            outputs['LocalisationVegetationExtraction'] = qgsUtils.loadVectorLayer(temp_path_loc_veg)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
        
           # Buffer de 5m autour du bati
            temp_path_buf_bati = QgsProcessingUtils.generateTempFilename('temp_path_buf_bati.gpkg')
            qgsTreatments.applyBufferFromExpr(outputs['LocalisationBatiExtraction'], 5, temp_path_buf_bati, context=context,feedback=feedback)
            outputs['BufferBati5m'] =  qgsUtils.loadVectorLayer(temp_path_buf_bati)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
           # Différence entre la végétation et le bati bufferisé pour enlever les zones qui se chevauches
            temp_path_diff_veg_bati = QgsProcessingUtils.generateTempFilename('temp_path_diff_veg_bati.gpkg')
            qgsTreatments.applyDifference(outputs['LocalisationVegetationExtraction'], outputs['BufferBati5m'], temp_path_diff_veg_bati, context=context,feedback=feedback)
            outputs['VegetationWithoutBati'] =  qgsUtils.loadVectorLayer(temp_path_diff_veg_bati)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Réparer les géométries
            temp_path_diff_veg_bati_fixed = QgsProcessingUtils.generateTempFilename('temp_path_diff_veg_bati_fixed.gpkg')
            qgsTreatments.fixGeometries(outputs['VegetationWithoutBati'],temp_path_diff_veg_bati_fixed, context=context,feedback=feedback)
            outputs['RepairVegetationWithoutBati'] = qgsUtils.loadVectorLayer(temp_path_diff_veg_bati_fixed)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
            
            if parameters[self.HEIGHT_FIELD_VEGETATION] != "" and parameters[self.HEIGHT_FIELD_VEGETATION] is not None and parameters[self.HEIGHT_FIELD_VEGETATION] != NULL:
                formula = '"'+parameters[self.HEIGHT_FIELD_VEGETATION]+'"'
            else:
                formula = parameters[self.DEFAULT_HEIGHT_VEGETATION]
            
            # on ajoute le champ HAUTEUR temporaire à la végétation pour après la fusion
            temp_path_diff_veg_bati_h = QgsProcessingUtils.generateTempFilename('temp_path_diff_veg_bati_h.gpkg')
            qgsTreatments.applyFieldCalculator(outputs['RepairVegetationWithoutBati'], 'h_vegetation_temp', temp_path_diff_veg_bati_h, formula, 6, 2, 0, context=context,feedback=feedback)
            outputs['RepairVegetationWithoutBati'] = qgsUtils.loadVectorLayer(temp_path_diff_veg_bati_h)
           
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
            # Union
            temp_path_union_veg_bati = QgsProcessingUtils.generateTempFilename('temp_path_union_veg_bati.gpkg')
            qgsTreatments.applyUnion(outputs['CalculFieldHeightBatiReplaceNullByMedian'], outputs['RepairVegetationWithoutBati'], temp_path_union_veg_bati, context=context, feedback=feedback)
            outputs['VectorToRasterize'] = qgsUtils.loadVectorLayer(temp_path_union_veg_bati)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
                
             # on récupère le champ Hauteur temporaire de la végétation
            formula = 'CASE\r\n\tWHEN  '+""+parameters[self.HEIGHT_FIELD_BATI]+""+' IS NULL THEN "h_vegetation_temp"\r\n\tELSE '+""+parameters[self.HEIGHT_FIELD_BATI]+""+'\r\nEND\r\n'
            temp_path_veg = QgsProcessingUtils.generateTempFilename('temp_path_veg.gpkg')
            qgsTreatments.applyFieldCalculator(outputs['VectorToRasterize'], parameters[self.HEIGHT_FIELD_BATI], temp_path_veg, formula, 6, 2, 0, context=context,feedback=feedback)
            outputs['VectorToRasterize'] = qgsUtils.loadVectorLayer(temp_path_veg)
            # self.results['VectorToRasterize'] = qgsUtils.loadVectorLayer(temp_path_veg)
            
            step+=1
            feedback.setCurrentStep(step)
            if feedback.isCanceled():
                return {}
            
        else: # on utilise seulement le bati
            outputs['VectorToRasterize'] = outputs['CalculFieldHeightBatiReplaceNullByMedian']
            step+=8
            feedback.setCurrentStep(step)            
        
        # Rastériser (remplacement avec attribut)
        self.results[self.OUTPUT_RASTER_MNS] = qgsTreatments.applyRasterizeOver(outputs['VectorToRasterize'],outputs[self.SLICED_RASTER], parameters[self.HEIGHT_FIELD_BATI], context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Rasteriser (vecteur vers raster)
        # prendre la résolution du raster en hauteur/largeur
        resolution = self.inputRasterMNT.rasterUnitsPerPixelX()
        self.results[self.OUTPUT_RASTER_BATI] = qgsTreatments.applyRasterization(outputs['VectorToRasterize'], self.outputRasterBati, outputs['RasterExtent'], resolution,
                                                                                        field=parameters[self.HEIGHT_FIELD_BATI],burn_val=0,nodata_val=0, 
                                                                                        context=context,feedback=feedback)  
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        print(step)
        
        return self.results

    def name(self):
        return 'CalculMNS'

    def displayName(self):
        return self.tr('Calcul of MNS')

    def group(self):
        return  self.tr('Visibility Light Sources')

    def groupId(self):
        return 'VisibilityLightSources'
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return CalculMNS()

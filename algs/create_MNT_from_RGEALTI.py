"""
Model exported as python.
Name : create MNT from RGEALTI
Group : 
With QGIS : 32215
"""
from PyQt5.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingUtils
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSource
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles
import os

class createMNTfromRGEALTI(QgsProcessingAlgorithm):
    
    EXTENT_ZONE = 'ExtentZone'
    EXTENT_BUFFER = 'ExtentBuffer'
    GRID = 'Grid'
    FOLDER_MNT_FILES = 'FolderMntFiles'
    OUTPUT_RASTER_MNT = 'OutputRasterMNT'
    FIELD_DALLE = 'NOM_DALLE'
    
    results = {}
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterNumber(self.EXTENT_BUFFER, self.tr('Buffer to apply to extent, meters'), type=QgsProcessingParameterNumber.Double,optional=True, defaultValue=1000))
        self.addParameter(QgsProcessingParameterVectorLayer(self.GRID, self.tr('grids'), defaultValue=None))
        
        self.addParameter(QgsProcessingParameterFile(self.FOLDER_MNT_FILES, self.tr('folder MNT ASC'), behavior=QgsProcessingParameterFile.Folder, fileFilter='Tous les fichiers (*.*)', defaultValue=None))
        
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER_MNT, 'Raster MNT', createByDefault=True, defaultValue=None))

    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1]        
        self.inputGrid = self.parameterAsVectorLayer(parameters, self.GRID, context)
        self.outputRasterMNT = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER_MNT,context)
        
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)
        outputs = {}

        self.parseParams(parameters, context, feedback)
        
        
         # Tampon optionnel autour de la zone d'emprise pour prendre plus de dalles
        if parameters[self.EXTENT_BUFFER] is not None and parameters[self.EXTENT_BUFFER] != NULL and parameters[self.EXTENT_BUFFER] > 0:
            temp_path_buf = QgsProcessingUtils.generateTempFilename('temp_path_buf.gpkg')
            # if self.inputExtent.crs().authid() != "EPSG:2154": # on reprojette le input
                # extent_zone = QgsProcessingUtils.generateTempFilename('extent_zone.gpkg')
                # qgsTreatments.applyReprojectLayer(self.inputExtent,QgsCoordinateReferenceSystem('EPSG:2154'), extent_zone, context=context,feedback=feedback)
                # self.inputExtent = qgsUtils.loadVectorLayer(extent_zone)
            qgsTreatments.applyBufferFromExpr(self.inputExtent,parameters[self.EXTENT_BUFFER], temp_path_buf,context=context,feedback=feedback)
            outputs[self.EXTENT_ZONE] =  qgsUtils.loadVectorLayer(temp_path_buf)
        else:
            outputs[self.EXTENT_ZONE] = self.inputExtent
        
        # Extraire par localisation
        temp_file_extract = QgsProcessingUtils.generateTempFilename('temp_file_extract.gpkg')
        qgsTreatments.extractByLoc(self.inputGrid, outputs[self.EXTENT_ZONE], temp_file_extract, context=context,feedback=feedback)
        layer = qgsUtils.loadVectorLayer(temp_file_extract)

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
        
        # Remplacement des "\\" par des "/" dans le chemin du dossier
        temp_path_folder = parameters[self.FOLDER_MNT_FILES].split("\\")
        temp_path_folder = '/'.join(temp_path_folder)
        
        # Récupération des indices des dalles selectionnées
        # Ajoute les noms des fichiers asc en fonction de la sélection
        list_grids_raster = []
        fields = layer.fields()
        selected_grids_index = []
        if fields.indexOf(self.FIELD_DALLE) > -1:
            features = layer.getFeatures()
            for feature in features:
                field_value = feature[self.FIELD_DALLE]
                selected_grids_index.append(field_value[20:29])
            list_grids_raster = []
            for grid_index in selected_grids_index:
                for file in os.listdir(temp_path_folder):
                    if grid_index in file and file.endswith('.asc'):
                        list_grids_raster.append(temp_path_folder+'/'+file)
                        break
            
        
        # Construire un vecteur virtuel
        outputs['ConstruireUnVecteurVirtuel'] = qgsTreatments.applyBuildVirtualRaster(list_grids_raster, QgsProcessing.TEMPORARY_OUTPUT, crs=layer.crs(), context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Convertir le raster virtuel en raster
        self.results['RasterMNT'] = qgsTreatments.applyTranslate(outputs['ConstruireUnVecteurVirtuel'], self.outputRasterMNT,data_type=0,nodata_val=None, crs=layer.crs(), options='COMPRESS=DEFLATE', context=context,feedback=feedback)
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        return self.results

    def name(self):
        return 'createMNTfromRGEALTI'

    def displayName(self):
        return self.tr('Create MNT from RGEALTI')

    def group(self):
        return self.tr('Misc')

    def groupId(self):
        return 'Misc'
    
    def tr(self, string):
        return QCoreApplication.translate(self.__class__.__name__, string)
        
    def createInstance(self):
        return createMNTfromRGEALTI()

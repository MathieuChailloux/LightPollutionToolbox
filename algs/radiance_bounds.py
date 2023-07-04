"""
Name : Seuils de radiance
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
from qgis.core import QgsProcessingParameterRasterDestination
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingUtils
from qgis.core import Qgis
from qgis.core import QgsProject
from qgis import processing
from ..qgis_lib_mc import utils, qgsUtils, qgsTreatments, styles

class RadianceBounds(QgsProcessingAlgorithm):
    
    RASTER_INPUT = 'ImageSat'

    BOUNDS = 'Bounds'
    
    EXTENT_ZONE = 'ExtentZone'
    SLICED_RASTER = 'SlicedRaster'

    OUTPUT_RASTER = 'OutputRaster'
    

    results = {}
    
    def initAlgorithm(self, config=None):
    
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.TypeVectorPolygon], defaultValue=None, optional=True))

        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Satellite Image'),defaultValue=None))

        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER, self.tr('Raster bounds'), defaultValue=None))
        
        self.addParameter(QgsProcessingParameterNumber(self.BOUNDS, self.tr('Radiance classification'), type=QgsProcessingParameterNumber.Double, defaultValue=25))


    def parseParams(self, parameters, context, feedback):
        self.inputExtent = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1]  
        self.inputRaster = self.parameterAsRasterLayer(parameters, self.RASTER_INPUT, context)
        self.outputRaster = self.parameterAsOutputLayer(parameters,self.OUTPUT_RASTER,context)
    
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(2, model_feedback)
        outputs = {}
        
        self.parseParams(parameters, context, feedback)

        # Si emprise non présente
        if self.inputExtent is None or self.inputExtent == NULL:
            outputs[self.SLICED_RASTER] = self.inputRaster # le raster n'est pas découpé
            
        else:
            # Découper un raster selon une emprise
            outputs[self.SLICED_RASTER] = qgsTreatments.applyClipRasterByExtent(self.inputRaster, self.inputExtent, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        #Si radiance > seuil  : 1 Sinon 0
        formula = '1*(logical_and(A>= '+str(parameters[self.BOUNDS])+', True))'
        outputs['CalculRasterMask'] =  qgsTreatments.applyRasterCalc(outputs[self.SLICED_RASTER], self.outputRaster, formula, out_type=Qgis.UInt16, context=context,feedback=feedback)
        self.results['Raster'] = outputs['CalculRasterMask']
        
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}
            
        
        return self.results

    def name(self):
        return 'RadianceBounds'

    def displayName(self):
        return self.tr('Radiance Bounds')
        
    def group(self):
        return self.tr('Utils Light Pollution Indicators')

    def groupId(self):
        return 'utilsLightPollutionIndicators'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate(self.__class__.__name__, string)
        
    def createInstance(self):
        return RadianceBounds()

    # def postProcessAlgorithm(self,context,feedback):
        # QgsProject.instance().addMapLayer(self, addToLegend=True)
        # print('postProcessAlgorithm')
        # return self.results
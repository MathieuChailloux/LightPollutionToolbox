"""
Name : Pixels de radiance vers points
Group : POLLUM
With QGIS : 40203
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import QgsProcessing
from qgis.core import NULL
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import Qgis

from ..qgis_lib import qgsTreatments

class RadianceToPoints(QgsProcessingAlgorithm):
    
    RASTER_INPUT = 'ImageSat'
    THRESHOLD = 'Threshold'
    EXTENT_ZONE = 'ExtentZone'
    CUT_RASTER = 'SlicedRaster'
    MASKED_RASTER = 'MaskedRaster'
    OUTPUT_VECTOR = 'OutputVector'
    

    results = {}
    
    def initAlgorithm(self, config=None):
    
        self.addParameter(QgsProcessingParameterFeatureSource(self.EXTENT_ZONE, self.tr('Extent zone'), [QgsProcessing.SourceType.TypeVectorPolygon], defaultValue=None, optional=True))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_INPUT,self.tr('Satellite image'),defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT_VECTOR, self.tr('Radiance points'), defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber(self.THRESHOLD, self.tr('Radiance threshold'), type=QgsProcessingParameterNumber.Type.Double, defaultValue=30))


    def parseParams(self, parameters, context, feedback):
        self.AreaOfInterest = qgsTreatments.parameterAsSourceLayer(self, parameters,self.EXTENT_ZONE,context,feedback=feedback)[1]  
        self.inputRaster = self.parameterAsRasterLayer(parameters, self.RASTER_INPUT, context)
        self.outputVector = self.parameterAsOutputLayer(parameters,self.OUTPUT_VECTOR,context)
    
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        step = 0
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)
        outputs = {}
        
        self.parseParams(parameters, context, feedback)

        # Si emprise non présente
        if self.AreaOfInterest is None or self.AreaOfInterest == NULL:
            outputs[self.CUT_RASTER] = self.inputRaster # le raster n'est pas découpé
            
        else:
            # Découper un raster selon une emprise
            outputs[self.CUT_RASTER] = qgsTreatments.applyClipRasterByPolygon(self.inputRaster, self.AreaOfInterest, QgsProcessing.TEMPORARY_OUTPUT, context=context,feedback=feedback)
            
        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        # Mettre du nodata à la place des valeurs en dessous du seuil
        formula = f'(A >= {parameters[self.THRESHOLD]}) * A'
        outputs[self.MASKED_RASTER] = qgsTreatments.applyRasterCalcAB(outputs[self.CUT_RASTER], None, QgsProcessing.TEMPORARY_OUTPUT, formula, 0, out_type=Qgis.DataType.UInt16, context=context,feedback=feedback)

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        outputs['Points'] = qgsTreatments.applyPixelsToPoints(outputs[self.MASKED_RASTER], self.outputVector, context=context, feedback=feedback)
        self.results[self.OUTPUT_VECTOR] = outputs['Points']

        step+=1
        feedback.setCurrentStep(step)
        if feedback.isCanceled():
            return {}

        return self.results

    def name(self):
        return 'RadianceToPoints'

    def displayName(self):
        return self.tr('Radiance to points')
        
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
        return RadianceToPoints()

    # def postProcessAlgorithm(self,context,feedback):
        # QgsProject.instance().addMapLayer(self, addToLegend=True)
        # print('postProcessAlgorithm')
        # return self.results

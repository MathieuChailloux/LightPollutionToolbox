
from PyQt5.QtCore import QCoreApplication, QVariant

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterFile,
                       QgsProcessingException,
                       QgsField)
                       

class FluxEstimationAlgorithm(QgsProcessingAlgorithm):                           

    LIGHTING = 'LIGHTING'
    FLUX_FIELD_NAME = 'FLUX_FIELD_NAME'
    OVERWRITE = 'OVERWRITE'
    LIGHT_TYPE_FIELD = 'LIGHT_TYPE_FIELD'
    LIGHT_TYPE_ASSOC = 'LIGHT_TYPE_ASSOC'
    FLUX_ASSOC = 'FLUX_ASSOC'
    OUTPUT = 'OUTPUT'
    
    LAMP_TYPE_FIELD = 'Lampe - Modèle lampe'
    LAMP_PW_FIELD = 'Lampe - Puissance lampe'
    base_flux = {
        "IODURES METALLIQUES" : 90,
        "BALLON FLUO" : 60,
        "QUARTZ HALOGENE" : 80,
        "DICHROÏQUE" : 15,
        "FLUO,COMPACTE" : 70,
        "TUBE FLUORESCENT" : 90,
        "TRES BASSE TENSION" : 300,
        "PAR" : 60
    }
        
    shp_flux_assoc = [ (50,80), (70,90), (100,100), (150,110), (250,120), (400,120), (600,130) ]
        
# LED
# SODIUM BLANC
# SODIUM BASSE PRESSION

    
    
    def getSHPFlux(self,pw):
        pw_int = int(pw)
        if pw_int <= 0:
            return 0
        for cpt, (k,v) in enumerate(self.shp_flux_assoc):
            if k == pw_int:
                return v
            elif k > pw_int:
                if cpt == 0:
                    return v
                else:
                    prev_v = self.shp_flux_assoc[cpt-1][1]
                    return (v + prev_v) / 2
        if pw_int > 600:
            return 130
        else:   
            raise QgsProcessingException("Unexpected power : " + str(pw_int)+ " " + str(k) + " " + str(v))
    
    def getSBPFlux(self,pw):
        return (pw * 0.4) + 107
    
    def getLEDFlux(self,feat):
        return 160
        
    def getFluxEff(self,feat,feedback):
        lamp_type = feat[self.LAMP_TYPE_FIELD]
        pw = feat[self.LAMP_PW_FIELD]
        if lamp_type in self.base_flux:
            return self.base_flux[lamp_type]
        elif lamp_type in ["SODIUM HAUTE PRESSION"]:
            return self.getSHPFlux(pw)
        elif lamp_type in ["SODIUM BLANC", "SODIUM BASSE PRESSION"]:
            return self.getSBPFlux(pw)
        elif lamp_type in ["LED"]:
            return self.getLEDFlux(feat)
        else:
            feedback.pushInfo("Could not compute flux efficiency for " + str(feat))
            return 0
    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LIGHTING,
                self.tr('Lighting layer')))
        self.addParameter(
            QgsProcessingParameterString(
                self.FLUX_FIELD_NAME,
                self.tr('Flux field name'),
                defaultValue="flux"))
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OVERWRITE,
                self.tr('Edit layer in place (new layer if unchecked)'),
                defaultValue=False))
        # self.addParameter(
            # QgsProcessingParameterField(
                # self.LIGHT_TYPE_FIELD,
                # description=self.tr('Light type field'),
                # defaultValue=self.DEFAULT_LIGHT_TYPE,
                # parentLayerParameterName=self.LIGHTING))
        # self.addParameter(
            # QgsProcessingParameterFile(
                # self.LIGHT_TYPE_ASSOC,
                # self.tr('Association file (light type -> light type)')))
        # self.addParameter(
            # QgsProcessingParameterFile(
                # self.FLUX_ASSOC,
                # self.tr('Association file (light type -> flux)')))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer'),
                optional=True))
                
    def processAlgorithm(self, parameters, context, feedback):
        
        # Parameters
        lighting = self.parameterAsVectorLayer(parameters, self.LIGHTING, context)
        fieldname = self.parameterAsString(parameters,self.FLUX_FIELD_NAME,context)
        if not fieldname:
            raise QgsProcessingException("No field given for light flux")
        overwrite = self.parameterAsBool(parameters, self.OVERWRITE, context)
        
        field_exists = fieldname in lighting.fields().names()
        
        if not field_exists:
            flux_field = QgsField(fieldname, QVariant.Double)
            lighting.dataProvider().addAttributes([flux_field])
            lighting.updateFields()
        elif overwrite:
            pass
        else:
            raise QgsProcessingException("Flux field already exists")
        
        lighting.startEditing()
        for feat in lighting.getFeatures():
            try:
                pw = feat[self.LAMP_PW_FIELD]
                #feedback.pushDebugInfo(str(pw))
                if pw:
                    flux_eff = self.getFluxEff(feat,feedback)
                    flux = flux_eff * pw
                else:
                    flux = 0
            except ValueError:
                flux = 0
            feat[fieldname] = flux
            lighting.updateFeature(feat)
        
        feedback.pushInfo("")
        lighting.commitChanges()
            
        return { self.OUTPUT : None }
            
    def name(self):
        return 'Light Flux Estimation'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return FluxEstimationAlgorithm()
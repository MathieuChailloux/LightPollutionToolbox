
import os, csv, re

from PyQt5.QtCore import QCoreApplication, QVariant

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterFile,
                       #QgsProcessingParameterDateTime,
                       QgsProcessingException,
                       QgsField)
                       

class FluxEstimationAlgorithm(QgsProcessingAlgorithm):                           

    LIGHTING = 'LIGHTING'
    FLUX_FIELD_NAME = 'FLUX_FIELD_NAME'
    OVERWRITE = 'OVERWRITE'
    LIGHT_TYPE_FIELD = 'LIGHT_TYPE_FIELD'
    LIGHT_TYPE_ASSOC = 'LIGHT_TYPE_ASSOC'
    LED_ASSOC = 'LED_ASSOC'
    FLUX_ASSOC = 'FLUX_ASSOC'
    OUTPUT = 'OUTPUT'
    
    DEFAULT_LED_ASSOC = "C:/Users/fdrmc/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/LightPollutionToolbox/assets/LED_eff.csv"
    
    LAMP_TYPE_FIELD = 'Lampe - Modèle lampe'
    LAMP_MODEL_FIELD = 'Luminaire - Libellé luminaire'
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

    led_flux_eff = {}

    def parseLEDFile(self,fname,feedback):
        fieldnames = ['Marque','Modele','Eff']
        self.led_flux_eff = {}
        if os.path.isfile(fname):
            with open(fname,newline='') as csvfile:
                reader = csv.DictReader(csvfile,fieldnames=fieldnames,delimiter=';')
                for row in reader:
                    try:
                        model, eff = row['Modele'], float(row['Eff'])
                        if model:
                            self.led_flux_eff[model] = eff
                    except ValueError:
                        feedback.pushDebugInfo("Could not parse " + str(row))
                    except TypeError:
                        feedback.pushDebugInfo("Could not parse " + str(row))
        else:
            raise QgsProcessingException("File " + str(fname) + " does not exist")
    
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
        lamp_model = str(feat[self.LAMP_MODEL_FIELD])
        if lamp_model in self.led_flux_eff:
            return self.led_flux_eff[lamp_model]
        for k, v in self.led_flux_eff.items():
            if len(k) > 3 and lamp_model.startswith(k):
                return v
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
            QgsProcessingParameterFile(
                self.LED_ASSOC,
                self.tr('LED efficacy association file (LED model -> luminous efficacy)'),
                defaultValue=self.DEFAULT_LED_ASSOC))
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
        filename = self.parameterAsFile(parameters,self.LED_ASSOC,context)
        
        if filename:
            self.parseLEDFile(filename,feedback)
            feedback.pushDebugInfo(str(self.led_flux_eff))
        else:
            feedback.pushInfo("No file given for LED light efficacy")
        
        flux_eff_name = 'flux_eff'
        flux_eff_field = QgsField(flux_eff_name, QVariant.Double)
        new_fields = [flux_eff_field]
        
        field_exists = fieldname in lighting.fields().names()
        if not field_exists:
            flux_field = QgsField(fieldname, QVariant.Double)
            new_fields.append(flux_field)
        elif overwrite:
            pass
        else:
            raise QgsProcessingException("Flux field already exists")
        lighting.dataProvider().addAttributes(new_fields)
        lighting.updateFields()
        
        lighting.startEditing()
        for feat in lighting.getFeatures():
            flux_eff = 0
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
            feat[flux_eff_name] = flux_eff
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
        
        

class FluxTimeAlgorithm(QgsProcessingAlgorithm):

    LIGHTING = 'LIGHTING'
    FLUX_FIELD = 'FLUX_FIELD'
    SHUTDOWN_FIELD = 'SHUTDOWN_FIELD'
    HOUR = 'HOUR'
    OVERWRITE = 'OVERWRITE'
    OUTPUT = 'OUTPUT'
    
    def getHourFlux(self,feat,hour,feedback):
        flux = feat[flux_field]
        shutdown = feat[shutdown_field]
        feedback.pushDebugInfo("feedback = " + str(feedback))
        if shutdown:
            # regexp
            pattern = "\(([AE\d+])\,(\d+)\)\;(\d*)"
            res_match = re.match(pattern,shutdown)
            for (inf, sup), coeff in res_match:
                pass
        else:
            return flux
            
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LIGHTING,
                self.tr('Lighting layer')))
        self.addParameter(
            QgsProcessingParameterString(
                self.FLUX_FIELD,
                self.tr('Flux field name')))
        self.addParameter(
            QgsProcessingParameterString(
                self.SHUTDOWN_FIELD,
                self.tr('Shutdown field')))
        self.addParameter(
            QgsProcessingParameterDateTime(
                self.HOUR,
                self.tr('Time for computation'),
                type=QgsProcessingParameterDateTime.Time))
                
        
    
    def processAlgorithm(self, parameters, context, feedback):
    
        # Parameters
        lighting = self.parameterAsVectorLayer(parameters, self.LIGHTING, context)
        flux_field = self.parameterAsString(parameters,self.FLUX_FIELD,context)
        shutdown_field = self.parameterAsString(parameters,self.SHUTDOWN_FIELD,context)
        hour = self.parametersAsDateTime(parameters,self.HOUR,context)
        
        for feat in lighting.getFeatures():
            flux = feat[flux_field]
            coeff = self.getHourFlux(base_flux)
        
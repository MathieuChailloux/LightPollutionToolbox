
import os, csv, re, datetime

from PyQt5.QtCore import QCoreApplication, QVariant

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       #QgsProcessingParameterDateTime,
                       QgsProcessingException,
                       QgsField)
                       

        
class FluxEstimAlg(QgsProcessingAlgorithm):

    def group(self):
        return self.tr('Light Flux Estimation')
        
    def groupId(self):
        return self.tr('fluxEstim')

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
        
        
class FluxEstimationAlgorithm(FluxEstimAlg):                           

    LIGHTING = 'LIGHTING'
    FLUX_FIELD_NAME = 'FLUX_FIELD_NAME'
    OVERWRITE = 'OVERWRITE'
    LIGHT_TYPE_FIELD = 'LIGHT_TYPE_FIELD'
    LIGHT_TYPE_ASSOC = 'LIGHT_TYPE_ASSOC'
    LED_ASSOC = 'LED_ASSOC'
    FLUX_ASSOC = 'FLUX_ASSOC'
    OUTPUT = 'OUTPUT'
    
    DEFAULT_LED_ASSOC = "C:/Users/fdrmc/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/LightPollutionToolbox/assets/LED_eff.csv"
    
    LAMP_TYPE_FIELD = 'Lampe - Modele lampe'
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
        return 'fluxEstim'

    def displayName(self):
        return self.tr('Light Flux Estimation')

    def createInstance(self):
        return FluxEstimationAlgorithm()
        
        

class FluxTimeAlgorithm(FluxEstimAlg):

    LIGHTING = 'LIGHTING'
    FLUX_FIELD = 'FLUX_FIELD'
    SHUTDOWN_FIELD = 'SHUTDOWN_FIELD'
    HOUR = 'HOUR'
    SUNSET = 'SUNSET'
    SUNRISE = 'SUNRISE'
    OUTPUT_FIELD = 'OUTPUT_FIELD'
    OVERWRITE = 'OVERWRITE'
    OUTPUT = 'OUTPUT'
    
    DEFAULT_SUNSET = 20
    DEFAULT_SUNRISE = 7
    
    pattern = re.compile("\(([AE\d]+)-([AE\d]+)\),(\d+)")
    
    def getHourFlux(self,flux,shutdown,hour,sunset,sunrise,feedback):
        #feedback.pushDebugInfo("feedback = " + str(feedback))
        if not flux or not shutdown:
            return flux
        if True:
            return flux
        if shutdown:
            # regexp
            feedback.pushDebugInfo("Shutdown = " + str(shutdown))
            shutdown = shutdown[1:-1]
            feedback.pushDebugInfo("Shutdown = " + str(shutdown))
            ranges = re.split(';',shutdown)
            for range in ranges:
                res_match = pattern.match(range)
                if not res_match:
                    feedback.pushInfo("Could not find matching range in " + str(range))
                    return flux
                start = res_match.group(1)
                end = res_match.group(2)
                coeff = int(res_match.group(3))
                feedback.pushDebugInfo("start = " + str(start))
                feedback.pushDebugInfo("end = " + str(end))
                feedback.pushDebugInfo("coeff = " + str(coeff))
                try:
                    start_time = sunset if start in ["A","E"] else int(start)
                    # start_time = datetime.time(hour=sstart)
                    end_time = sunrise if end in ["A","E"] else int(end)
                    # end_time = datetime.time(hour=eend)
                    # hour_time = datetime.time(hour=hour)
                    hour_time = hour
                    feedback.pushDebugInfo("start_time = " + str(start_time))
                    feedback.pushDebugInfo("end_time = " + str(end_time))
                    feedback.pushDebugInfo("hour_time = " + str(hour_time))
                    if (start_time > end_time and (start_time <= hour_time or hour_time < end_time)):
                        new_flux = int(flux * (coeff / 100))
                        return new_flux
                    elif (start_time <= hour_time and hour_time < end_time):
                        new_flux = int(flux * (coeff / 100))
                        return new_flux
                    else:
                        continue
                except ValueError as e:
                    feedback.pushInfo("Ignoring error " + str(e))
                    continue
                    #raise e
            return flux
            
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.LIGHTING,
                self.tr('Lighting layer')))
        self.addParameter(
            QgsProcessingParameterField(
                self.FLUX_FIELD,
                self.tr('Flux field name'),
                parentLayerParameterName=self.LIGHTING,
                defaultValue="flux_int"))
        self.addParameter(
            QgsProcessingParameterField(
                self.SHUTDOWN_FIELD,
                self.tr('Shutdown field'),
                parentLayerParameterName=self.LIGHTING,
                defaultValue="Abaissement"))
        # self.addParameter(
            # QgsProcessingParameterDateTime(
                # self.HOUR,
                # self.tr('Time for computation'),
                # type=QgsProcessingParameterDateTime.Time))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HOUR,
                self.tr('Time for computation'),
                type=QgsProcessingParameterNumber.Integer))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SUNSET,
                self.tr('Sunset hour'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=self.DEFAULT_SUNSET))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SUNRISE,
                self.tr('Sunrise hour'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=self.DEFAULT_SUNRISE))
        self.addParameter(
            QgsProcessingParameterString(
                self.OUTPUT_FIELD,
                self.tr('Output flux field name'),
                defaultValue="flux_test"))
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OVERWRITE,
                self.tr('Overwrites outptut values if existing'),
                defaultValue=False))
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer'),
                optional=True))
                
        
    
    def processAlgorithm(self, parameters, context, feedback):
    
        # Parameters
        lighting = self.parameterAsVectorLayer(parameters, self.LIGHTING, context)
        flux_field = self.parameterAsString(parameters,self.FLUX_FIELD,context)
        shutdown_field = self.parameterAsString(parameters,self.SHUTDOWN_FIELD,context)
        #hour = self.parametersAsDateTime(parameters,self.HOUR,context)
        hour = self.parameterAsInt(parameters,self.HOUR,context)
        sunset = self.parameterAsInt(parameters,self.SUNSET,context)
        sunrise = self.parameterAsInt(parameters,self.SUNRISE,context)
        out_fieldname = self.parameterAsString(parameters,self.OUTPUT_FIELD,context)
        overwrite_flag = self.parameterAsBool(parameters,self.OVERWRITE,context)
        
        # Creates new field        
        field_exists = out_fieldname in lighting.fields().names()
        if not field_exists:
            new_field = QgsField(out_fieldname, QVariant.Int)
            lighting.dataProvider().addAttributes([new_field])
            lighting.updateFields()
        elif not overwrite_flag:
            raise QgsProcessingException("Flux '" + out_fieldname + "'field already exists")
        lighting.updateFields()
        
        # Iteration on features
        lighting.startEditing()
        for feat in lighting.getFeatures():
            init_flux, shutdown = feat[flux_field], feat[shutdown_field]
            if not shutdown:
                feat[out_fieldname] = init_flux
            elif init_flux:
                flux_int = int(init_flux)
                # feedback.pushDebugInfo("Init : " + str(flux_int))
                new_flux = self.getHourFlux(flux_int,shutdown,hour,sunset,sunrise,feedback)
                # feedback.pushDebugInfo("New : " + str(new_flux))
                # if new_flux != init_flux:
                    # feedback.pushDebugInfo("Transfo " + str(init_flux) + " -> " + str(new_flux))
                feat[out_fieldname] = new_flux
            else:
                feat[out_fieldname] = None
            #feat[out_fieldname] = init_flux
            lighting.updateFeature(feat)
            #lighting.commitChanges()
           # pass
        feedback.pushInfo("")
        lighting.commitChanges()
            
        return { self.OUTPUT : None }
        
    def name(self):
        return 'fluxHour'

    def displayName(self):
        return self.tr('Light Flux Per Hour')
        
    def createInstance(self):
        return FluxTimeAlgorithm()
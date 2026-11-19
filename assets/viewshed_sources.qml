<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="Symbology|MapTips" version="3.44.15-Solothurn">
  <mapTip enabled="1"></mapTip>
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option value="" name="name" type="QString"/>
      <Option name="properties"/>
      <Option value="collection" name="type" type="QString"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling maxOversampling="2" enabled="false" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer nodataColor="" alphaBand="-1" classificationMin="0" opacity="0.7" band="1" type="singlebandpseudocolor" classificationMax="2000">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader colorRampType="DISCRETE" maximumValue="2000" classificationMode="1" minimumValue="0" clip="0" labelPrecision="0">
          <colorramp name="[source]" type="gradient">
            <Option type="Map">
              <Option value="14,98,106,255,rgb:0.054902,0.3843137,0.4156863,1" name="color1" type="QString"/>
              <Option value="239,24,13,255,hsv:0.00838888888888889,0.94642557412069883,0.93548485542076754,1" name="color2" type="QString"/>
              <Option value="ccw" name="direction" type="QString"/>
              <Option value="0" name="discrete" type="QString"/>
              <Option value="gradient" name="rampType" type="QString"/>
              <Option value="rgb" name="spec" type="QString"/>
              <Option value="0.0025;145,203,168,255,rgb:0.5686275,0.7960784,0.6588235,1;rgb;ccw:0.005;221,241,180,255,rgb:0.8666667,0.945098,0.7058824,1;rgb;ccw:0.01;254,223,153,255,rgb:0.9960784,0.8745098,0.6,1;rgb;ccw:0.025;245,144,83,255,rgb:0.9607843,0.5647059,0.3254902,1;rgb;ccw" name="stops" type="QString"/>
            </Option>
          </colorramp>
          <item color="#0e626a" alpha="255" label="Très faible" value="0"/>
          <item color="#91cba8" alpha="255" label="Très faible à faible" value="5"/>
          <item color="#ddf1b4" alpha="255" label="Faible" value="10"/>
          <item color="#fedf99" alpha="255" label="Modérée" value="20"/>
          <item color="#f59053" alpha="255" label="Forte" value="50"/>
          <item color="#ef180d" alpha="255" label="Très forte" value="50000"/>
          <rampLegendSettings prefix="" suffix="" direction="0" minimumLabel="" maximumLabel="" orientation="2" useContinuousLegend="1">
            <numericFormat id="basic">
              <Option type="Map">
                <Option name="decimal_separator" type="invalid"/>
                <Option value="6" name="decimals" type="int"/>
                <Option value="0" name="rounding_type" type="int"/>
                <Option value="false" name="show_plus" type="bool"/>
                <Option value="true" name="show_thousand_separator" type="bool"/>
                <Option value="false" name="show_trailing_zeros" type="bool"/>
                <Option name="thousand_separator" type="invalid"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast contrast="0" gamma="1" brightness="0"/>
    <huesaturation grayscaleMode="0" colorizeGreen="128" colorizeOn="0" colorizeBlue="128" saturation="0" invertColors="0" colorizeRed="255" colorizeStrength="100"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>

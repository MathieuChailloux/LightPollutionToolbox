<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44.15-Solothurn" styleCategories="Symbology|MapTips">
  <mapTip enabled="1"></mapTip>
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option type="QString" value="" name="name"/>
      <Option name="properties"/>
      <Option type="QString" value="collection" name="type"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling zoomedOutResamplingMethod="nearestNeighbour" maxOversampling="2" zoomedInResamplingMethod="nearestNeighbour" enabled="false"/>
    </provider>
    <rasterrenderer band="1" alphaBand="-1" classificationMax="2000" nodataColor="" type="singlebandpseudocolor" classificationMin="0" opacity="0.7">
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
        <colorrampshader labelPrecision="0" colorRampType="DISCRETE" minimumValue="0" maximumValue="2000" classificationMode="1" clip="0">
          <colorramp type="gradient" name="[source]">
            <Option type="Map">
              <Option type="QString" value="14,98,106,255,rgb:0.054902,0.3843137,0.4156863,1" name="color1"/>
              <Option type="QString" value="255,0,255,255,rgb:1,0,1,1" name="color2"/>
              <Option type="QString" value="ccw" name="direction"/>
              <Option type="QString" value="0" name="discrete"/>
              <Option type="QString" value="gradient" name="rampType"/>
              <Option type="QString" value="rgb" name="spec"/>
              <Option type="QString" value="0.005;221,241,180,255,rgb:0.8666667,0.945098,0.7058824,1;rgb;ccw:0.01;254,223,153,255,rgb:0.9960784,0.8745098,0.6,1;rgb;ccw:0.025;145,203,168,255,rgb:0.5686275,0.7960784,0.6588235,1;rgb;ccw:0.125;245,144,83,255,rgb:0.9607843,0.5647059,0.3254902,1;rgb;ccw:0.25;239,24,13,255,rgb:0.9372549,0.0941176,0.0509804,1;rgb;ccw" name="stops"/>
            </Option>
          </colorramp>
          <item alpha="255" label="Très faible" color="#0e626a" value="0"/>
          <item alpha="255" label="Faible" color="#ddf1b4" value="10"/>
          <item alpha="255" label="Modérée" color="#fedf99" value="20"/>
          <item alpha="255" label="Très faible à faible" color="#91cba8" value="50"/>
          <item alpha="255" label="Forte" color="#f59053" value="250"/>
          <item alpha="255" label="Forte à très forte" color="#ef180d" value="500"/>
          <item alpha="255" label="Très forte" color="#ff00ff" value="10000"/>
          <rampLegendSettings orientation="2" minimumLabel="" maximumLabel="" prefix="" useContinuousLegend="1" suffix="" direction="0">
            <numericFormat id="basic">
              <Option type="Map">
                <Option type="invalid" name="decimal_separator"/>
                <Option type="int" value="6" name="decimals"/>
                <Option type="int" value="0" name="rounding_type"/>
                <Option type="bool" value="false" name="show_plus"/>
                <Option type="bool" value="true" name="show_thousand_separator"/>
                <Option type="bool" value="false" name="show_trailing_zeros"/>
                <Option type="invalid" name="thousand_separator"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation grayscaleMode="0" invertColors="0" colorizeGreen="128" colorizeOn="0" colorizeBlue="128" saturation="0" colorizeRed="255" colorizeStrength="100"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>

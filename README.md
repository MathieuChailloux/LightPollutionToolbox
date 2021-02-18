
[[English](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/README.md) | [Français](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/README_fr.md)]

# Overview

*LightPollutionToolbox* is a QGIS 3 processing provider plugin.

*LightPollutionToolbox* provides multiple algorithms to characterize and map light pollution. It has been initially developped to check compliance with french regulations but is intended to go further and gather any treatments relative to light dispersal, public lighting, statistics, ... 

*LightPollutionToolbox* has been developed by Mathieu Chailloux ([*UMR TETIS*](https://www.umr-tetis.fr) / [*INRAE*](http://www.inrae.fr)) on mission for the [*French ecological network resource center*](http://www.trameverteetbleue.fr/).

# Documentation

Available documentation:
 - [Video tutorials](https://www.youtube.com/playlist?list=PLh9oFe6PuPCVSnbwOEN6aZ1hHkdg5qzg7)
 - [Notice about Light Flux Surfacic density (french only)](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/docs/fr/NoteDSFLI_INRAE.pdf)

# Algorithms

Main algorithms are:
 - *Classify lighting layer*: checks compliance of a lighting layer to french regulations indicators (Upward Light Ratio, light flux, color temperature)
 - *Light Flux Surfacic Density (from raw data)*: computes Light Flux Surfacic Density, another indicator from french regulation which allows a certain amount of flux depending on the surface to be lit, from raw data (lighting layer, roads layer, cadastre layer, ...)
 
 
*Statistics* group contains algorithms such as *Radiance Zonal Statistics* that compute radiance per surface/population from a satellite image (such as [NASA Black Marble](https://blackmarble.gsfc.nasa.gov/#product)) and a population layer.

*Light Flux Surfacic Density* group contains intermediate algorithms used to compute light flux surfacic density:
 - *Add cadastre selection*: adds a manual selection of cadastre plots to a surface layer
 - *Apply symbology to DSFL layer*: apply a predefined legend according to reglementation tresholds
 - *Light Flux surfacic density*: computes light flux surfacic desinty from lighting, reporting and surface layers
 - *Light Flux surfacic density (from surface)*: computes light flux surfacic desinty from lighting and surface layers
 - *Reporting per roads*: computes a reporting layer from roads layer
 - *Roads Extent (BDTOPO + Cadastre)*: computes surface layer from roads and cadastre layers
 - *Roads Extent (BDTOPO)*: computes surface layer from roads layer
 - *Roads Extent (Cadastre)*: computes surface layer from cadastre layer

# Sample data 

Sample data to compute light flux surfacic density is provided with plugin (directory *sample_data*).

# Contact

*Development* : Mathieu Chailloux (mathieu.chailloux@inrae.fr)

*Coordination* : Jennifer Amsallem (jennifer.amsallem@inrae.fr)

# Quotation

> Chailloux, M. & Amsallem, J. (2021) LightPollutionToolbox : a QGIS plugin to characterize light pollution

# Installation

*LightPollutionToolbox* must be installed from *QGIS* plugins menu.

# Developers

*LightPollutionToolbox* is based on submodule [*qgis_lib_mc*](https://github.com/MathieuChailloux/qgis_lib_mc)

To install git repository:  
> git clone https://github.com/MathieuChailloux/LightPollutionToolbox.git
>
> cd LightPollutionToolbox
>
> git clone https://github.com/MathieuChailloux/qgis_lib_mc.git

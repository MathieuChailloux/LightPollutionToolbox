
[[English](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/README.md) | [Français](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/README_fr.md)]

# Aperçu

*LightPollutionToolbox* est un plugin QGIS 3.

*LightPollutionToolbox* regroupe divers géotraitements pour caractériser et cartographier la pollution lumineuse. Développé initialement pour vérifier la conformité à la réglementation depuis des couches d'éclairage public, cet outil a vocation à évoluer et d'être augmenté de tout géotraitement pertinent sur la thématique pollution lumineuse et Trame noire.

*LightPollutionToolbox* a été développé par Mathieu Chailloux et Antoine Sensier ([*UMR TETIS*](https://www.umr-tetis.fr) / [*INRAE*](http://www.inrae.fr)) pour le [*Centre de ressources Trame verte et bleue*](http://www.trameverteetbleue.fr/).

# Documentation

Documentation disponible :
 - [Tutoriels vidéos sur la Densité Surfacique de Flux Lumineux Installée](https://www.youtube.com/playlist?list=PLh9oFe6PuPCVSnbwOEN6aZ1hHkdg5qzg7)
 - [Tutoriels vidéos sur les Indicateurs de Pollution Lumineuse](https://www.youtube.com/playlist?list=PLh9oFe6PuPCU_K-qqZBIKJWEuRJFRa4Gc)
 - [Note méthodologique sur la Densité Surfacique de Flux Lumineux Installée](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/docs/fr/NoteDSFLI_INRAE.pdf)
 - [Note méthodologique sur le calcul d'indicateurs de pollution lumineuse](https://github.com/MathieuChailloux/LightPollutionToolbox/blob/master/docs/fr/NoteIndicateursPOLLUM_INRAE_fr.pdf)

# Algorithmes Indicateurs de Pollution Lumineuse

Les Algorithmes sont disponibles dans la boite à outils de traitements ou via le bouton "LightPollutionToolbox" du menu.
Les 3 principaux indicateurs sont les suivants:
- Contribution au halo lumineux (Radiance)
  Fichier : ./algs/statistics_radiance_grid.py
- Emission dans le partie bleue du spectre
  Fichier : ./algs/statistics_blue_emission_grid.py
- Visibilité des sources lumineuses : ce traitement est divisés en 3 sous-traitements :
	- 1 : Calcul du MNS (Modèle Numérique de Surface) avec le MNT, le bati et éventuellement la végétation (opitonnel)
		  Fichier : ./algs/analyse_visibility_light_sources.py
	- 2 : Calcul du champ de visibilité (viewshed), une partie du code provient du plugin Viewshed analysis : https://www.zoran-cuckovic.from.hr/QGIS-visibility-analysis
		  Fichier : ./algs/analyse_visibility_light_sources.py
	- 3 : Nombre moyen de sources lumineuses par maille
		  Fichier : ./algs/analyse_visibility_light_sources.py

Il existe aussi 2 autres traitements dans le sous-menu "Utils Indicateurs de pollution lumineuse" de la bôite à outils :
- create MNT from RGE Alti : permet de créer un MNT à partir d'une zone d'emprise, de la dalles et du dossier MNT ASC de RGE Alti
  Fichier : ./algs/create_MNT_from_RGEALTI.py
- Pretreatments to remove dark zones : permet de mettre à 0 les pixels inférieurs à la médiane des pixels par bande
  Fichier : ./algs/pretreatments_dark_zones.py 
 
 
# Algorithmes DSFLI

Les 2 algorithmes principaux sont :
 - *Classify lighting layer* : vérifie la conformité d'une couche d'éclairage public à certains indicateurs de la réglementation (ULR, flux lumineux, température de couleur)
 - *Light Flux Surfacic Density (from raw data)* : calcul de la Densité Surfacique de Flux Lumineux Installé (DSFLI) depuis des données brutes

Le groupe *Statistics* a vocation à regrouper des traitements calculant des statistiques comme l'algorithme *Radiance Zonal Statistics* qui calcule la radiance par surface et par population depuis une image satellite (par exemple les [Black Marble de la NASA](https://blackmarble.gsfc.nasa.gov/#product) ) et un découpage territorial (par exemple couche de communes).

Le groupe *Light Flux Surfacic Density* regrouper les traitements intermédiaires permettant le calcul de la DSFLI :
 - *Add cadastre selection* : ajoute une sélection manuelle de parcelles cadastrales à une couche de surface
 - *Apply symbology to DSFL layer* : applique une légende prédéfinie reprenant les seuils réglementaires à une couche de DSFLI
 - *Light Flux surfacic density* : calcule la DSFLI depuis une couche d'éclairage public, une couche de rapportage et une couche de surface
 - *Light Flux surfacic density (from surface)* : calcule la DSFLI depuis une couche d'éclairage public et une couche de surface
 - *Reporting per roads* : construit une couche de rapportage en appliquant des tampons autour de routes
 - *Roads Extent (BDTOPO + Cadastre)* : construit une couche de surface depuis une couche de route de la BDTOPO et une couche de parcelles cadastrales
 - *Roads Extent (BDTOPO)* : construit une couche de surface depuis une couche de route de la BDTOPO
 - *Roads Extent (Cadastre)* : construit une couche de surface depuis une couche de parcelles cadastrales

La description détaillée des paramètres est disponible dans chaque algorithme.

# Contact

*Développement* : Mathieu Chailloux (mathieu.chailloux@inrae.fr) & Antoine Sensier (antoine.sensier@inrae.fr)

*Coordination* : Jennifer Amsallem (jennifer.amsallem@inrae.fr)

# Citation

> Chailloux, M. & Amsallem, J. (2021) LightPollutionToolbox : a QGIS plugin to characterize light pollution


# Installation

Pour installer *LightPollutionToolbox* dans *QGIS*, aller dans le menu *Extensions->Installer/Gérer les extensions->Installer depuis un zip* et sélectionner l'archive *LightPollutionToolbox.zip*.

Les algorithmes apparaissent alors dans la boîte à outils de traitement.

# Développeurs

*LightPollutionToolbox* dépend du sous-module [*qgis_lib_mc*](https://github.com/MathieuChailloux/qgis_lib_mc)

Pour installer le git :  
> git clone https://github.com/MathieuChailloux/LightPollutionToolbox.git
>
> cd LightPollutionToolbox
>
> git clone https://github.com/MathieuChailloux/qgis_lib_mc.git

Sous Windows, le répertoire des plugins *QGIS* est *C:/Users/user/AppData/Romaing/QGIS/QGIS3/profiles/default/python/plugins*.



# Aperçu

*LightPollutionToolbox* est un plugin QGIS 3 en cours de développement.

Plusieurs algorithmes sont actuellement disponibles :
 - *Light Flux estimation* : création d'un champ estimant le flux lumineux d'une couche de sources lumineuses en fonction des types, modèles (pour les LED) et puissance de lampe. Les valeurs sont codées en dur dans l'algorithme pour le moment mais seront paramétrables dans une prochaine version.
 - *Ligh Flux Surfacic Density* : estimation de la Densité Surfacique de Flux Lumineux (DSFL)

# Installation

Pour installer *LightPollutionToolbox* dans *QGIS*, aller dans le menu *Extensions->Installer/Gérer les extensions->Installer depuis un zip* et sélectionner l'archive *LightPollutionToolbox.zip*.

# Développeurs

*LightPollutionToolbox* dépend du sous-module [*qgis_lib_mc*](https://github.com/MathieuChailloux/qgis_lib_mc)

Pour installer le git :  
    $ git clone https://github.com/MathieuChailloux/LightPollutionToolbox.git
    $ cd LightPollutionToolbox
    $ git clone https://github.com/MathieuChailloux/qgis_lib_mc.git

#/***************************************************************************
# LightPollutionToolbox
#
# Light pollution indicators (focus on public lighting)
#							 -------------------
#		begin				: 2020-04-20
#		git sha				: $Format:%H$
#		copyright			: (C) 2020 by Mathieu Chailloux
#		email				: mathieu@chailloux.org
# ***************************************************************************/
#
#/***************************************************************************
# *																		 *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or	 *
# *   (at your option) any later version.								   *
# *																		 *
# ***************************************************************************/

#################################################
# Edit the following to match your sources lists
#################################################


#Add iso code for any locales you want to support here (space separated)
# default is no locales
# LOCALES = af
LOCALES =

# If locales are enabled, set the name of the lrelease binary on your system. If
# you have trouble compiling the translations, you may have to specify the full path to
# lrelease
#LRELEASE = lrelease
#LRELEASE = lrelease-qt4


# translation
SOURCES = \
	__init__.py \
	LightPollutionToolbox.py 

PLUGINNAME = LightPollutionToolbox

PY_FILES = \
	*.py

UI_FILES = \
	*.ui
	
MD_FILES = \
	*.md
		
EXTRAS = metadata.txt \
	lamp.png

EXTRA_DIRS = \
	docs \
	sample_data \
	icons \
	help

EXTRA_PY_DIRS = \
	algs \
	qgis_lib_mc \
	algs/DSFLI \
	algs/modules

EXCLUDE_DIRS = \
	sample_data/outputs \

EXCLUDE_FILES = \
	docs/fr/NoteDSFLI_25012021_v2.docx

COMPILED_RESOURCE_FILES = 

PEP8EXCLUDE=pydev,resources.py,conf.py,third_party,ui

COMMIT = $(shell git rev-parse HEAD)
LIB_COMMIT = $(shell cd qgis_lib_mc; git rev-parse HEAD; cd ..)
COMMIT_FILE = $(PLUGINNAME)/git-versions.txt

# QGISDIR points to the location where your plugin should be installed.
# This varies by platform, relative to your HOME directory:
#	* Linux:
#	  .local/share/QGIS/QGIS3/profiles/default/python/plugins/
#	* Mac OS X:
#	  Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins
#	* Windows:
#	  AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins'

QGISDIR=C:\Users\fdrmc\AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins

#################################################
# Normally you would not need to edit below here
#################################################

HELP = help/build/html

PLUGIN_UPLOAD = $(c)/plugin_upload.py

RESOURCE_SRC=$(shell grep '^ *<file'  | sed 's@</file>@@g;s/.*>//g' | tr '\n' ' ')

.PHONY: default archive

compile: $(COMPILED_RESOURCE_FILES)

%.py : %.qrc $(RESOURCES_SRC)
	pyrcc5 -o $*.py  $<

%.qm : %.ts
	$(LRELEASE) $<

test: compile transcompile
	@echo
	@echo "----------------------"
	@echo "Regression Test Suite"
	@echo "----------------------"

	@# Preceding dash means that make will continue in case of errors
	@-export PYTHONPATH=`pwd`:$(PYTHONPATH); \
		export QGIS_DEBUG=0; \
		export QGIS_LOG_FILE=/dev/null; \
		nosetests -v --with-id --with-coverage --cover-package=. \
		3>&1 1>&2 2>&3 3>&- || true
	@echo "----------------------"
	@echo "If you get a 'no module named qgis.core error, try sourcing"
	@echo "the helper script we have provided first then run make test."
	@echo "e.g. source run-env-linux.sh <path to qgis install>; make test"
	@echo "----------------------"


# The dclean target removes compiled python files from plugin directory
# also deletes any .git entry
dclean:
	@echo
	@echo "-----------------------------------"
	@echo "Removing any compiled python files."
	@echo "-----------------------------------"
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname "*.pyc" -delete
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname ".git" -prune -exec rm -Rf {} \;


archive:
	rm -f $(PLUGINNAME).zip
	rm -rf $(PLUGINNAME)
	mkdir -p $(PLUGINNAME)
	cp -vf $(PY_FILES) $(PLUGINNAME)
	cp -vf $(UI_FILES) $(PLUGINNAME)
	cp -vf $(MD_FILES) $(PLUGINNAME)
	cp -vf $(EXTRAS) $(PLUGINNAME)
	cp -vfr i18n $(PLUGINNAME)
	$(foreach EXTRA_PY_DIR,$(EXTRA_PY_DIRS), mkdir $(PLUGINNAME)/$(EXTRA_PY_DIR);)
	$(foreach EXTRA_PY_DIR,$(EXTRA_PY_DIRS), cp $(EXTRA_PY_DIR)/*.py $(PLUGINNAME)/$(EXTRA_PY_DIR);)
	$(foreach EXTRA_DIR,$(EXTRA_DIRS), cp -R $(EXTRA_DIR) $(PLUGINNAME)/;)
	$(foreach EXCLUDE_DIR,$(EXCLUDE_DIRS), rm -rf $(PLUGINNAME)/$(EXCLUDE_DIR);)
	$(foreach EXCLUDE_FILE,$(EXCLUDE_FILES), rm -f $(PLUGINNAME)/$(EXCLUDE_FILE);)
	echo "LightPollutionToolbox commit number "  > $(COMMIT_FILE)
	echo $(COMMIT) >> $(COMMIT_FILE)
	echo "\nqgis_lib_mc commit number "  >> $(COMMIT_FILE)
	echo $(LIB_COMMIT) >> $(COMMIT_FILE)
	zip -r $(PLUGINNAME).zip $(PLUGINNAME)

ui:
	pyuic5 -o Interface_dialog_base.py Interface_dialog_base.ui
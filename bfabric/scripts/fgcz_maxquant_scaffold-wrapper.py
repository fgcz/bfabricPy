#!/usr/bin/python3
# -*- coding: latin1 -*-

# Copyright (C) 2019 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/bfabric/scripts/fgcz_pd_wrapper.py $
# $Id: fgcz_pd_wrapper.py 2992 2017-08-17 13:37:36Z cpanse $

import logging
import logging.handlers
import os
import pprint
import re
import sys
import time
import urllib
from optparse import OptionParser
from lxml import etree
import yaml
from pathlib import Path
import hashlib
from io import StringIO, BytesIO
# import warnings

"""
requirements

"""

import unittest

class FgczMaxQuantScaffold:
    """
  input:

    """

    config = None
    scratchdir = None

    def __init__(self, config=None, scratch = "/scratch/MAXQUANT/"):



    def run(self):
      pass


scaffold_driver_templ_xml ='''
<?xml version="1.0" encoding="UTF-8"?>
<Scaffold pathsep="/" version="Scaffold_4.8.9">
    <Experiment analyzeWithSubsetDB="false" analyzeWithTandem="false"
        annotateWithGOA="false" condenseDataWhileLoading="true"
        connectToNCBI="false"
        experimentDisplayType="Total Spectrum Count"
        name="jonas_XwinLoaded_WU192418_individualCategories"
        peakListChargeStatesCalculated="false"
        peakListDeisotoped="false" protectDisplaySettings="false"
        protectExportSpectra="false" protectThresholds="false"
        proteinGrouping="protein-cluster-analysis"
        showDataLoadingPane="true" showNavigationPane="true"
        showProteinHomologyPane="true" showProteinsPane="true"
        showPublishPane="true" showQuantifyPane="true"
        showSampleNotes="true" showSamplesPane="true"
        showSpectraPane="false" showStatisticsPane="true" viewBioSamples="true">
        <FastaDatabase databaseAccessionRegEx=">([^\s]*)"
            databaseDescriptionRegEx=">[^\s]*[\s](.*)"
            databaseVersion="" id="db0" matchMethod="Regex"
            path="/scratch/FASTA/fgcz_9606_reviewed_cnl_contaminantNoHumanCont_20161209.fasta" useAutoParse="false"/>
        <BiologicalSample analyzeAsMudpit="false"
            category="20191015_002_HeLa_50_PreOmics_LK_3" database="db0"
            description="" name="20191015_002_HeLa_50_PreOmics_LK_3" quantitativeTechnique="Spectrum Counting">
            <InputFile maxQuantExperiment="20191015_002_HeLa_50_PreOmics_LK_3">WU192418/output-WU192418.zip</InputFile>
        </BiologicalSample>
        <BiologicalSample analyzeAsMudpit="false"
            category="20191015_004_HeLa_50_PreOmics_LK_1" database="db0"
            description="" name="20191015_004_HeLa_50_PreOmics_LK_1" quantitativeTechnique="Spectrum Counting">
            <InputFile maxQuantExperiment="20191015_004_HeLa_50_PreOmics_LK_1">WU192418/output-WU192418.zip</InputFile>
        </BiologicalSample>
        <BiologicalSample analyzeAsMudpit="false"
            category="20191015_008_HeLa_50_PreOmics_LK_2" database="db0"
            description="" name="20191015_008_HeLa_50_PreOmics_LK_2" quantitativeTechnique="Spectrum Counting">
            <InputFile maxQuantExperiment="20191015_008_HeLa_50_PreOmics_LK_2">WU192418/output-WU192418.zip</InputFile>
        </BiologicalSample>
        <BiologicalSample analyzeAsMudpit="false"
            category="20191015_009_HeLa_50_PreOmics_LK_4" database="db0"
            description="" name="20191015_009_HeLa_50_PreOmics_LK_4" quantitativeTechnique="Spectrum Counting">
            <InputFile maxQuantExperiment="20191015_009_HeLa_50_PreOmics_LK_4">WU192418/output-WU192418.zip</InputFile>
        </BiologicalSample>
        <DisplayThresholds id="thresh" minimumPeptideCount="1"
            peptideProbability="0.99" proteinProbability="0.96"/>
        <Export type="sf3"/>
    </Experiment>
</Scaffold>
'''

if __name__ == "__main__":
  pass
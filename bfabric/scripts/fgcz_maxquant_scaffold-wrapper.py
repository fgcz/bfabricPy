#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#

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

# import unittest

class FgczMaxQuantScaffold:
    """
  input:

    """

    config = None
    scratchdir = None
    fasta = None

    def __init__(self, fasta=''):
        self.fasta=fasta
        pass

    def getBiologicalSample(selfs, InputFile = None, category = '***BASENAME***'):

        scaffold_BiologicalSample = '''
        <BiologicalSample
            analyzeAsMudpit="false"
            category="20191015_002_HeLa_50_PreOmics_LK_3"
            database="db0"
            description=""
            name="20191015_002_HeLa_50_PreOmics_LK_3"
            quantitativeTechnique="Spectrum Counting">
            <InputFile 
                maxQuantExperiment="20191015_002_HeLa_50_PreOmics_LK_3">WU192418/output-WU192418.zip</InputFile>
        </BiologicalSample>
        '''

        pBioSample = etree.XML(scaffold_BiologicalSample)

        eInputFile = pBioSample.find("InputFile")

        if eInputFile is None:
            raise TypeError

        eInputFile.text = '*** file {} ***'.format(InputFile)
        eInputFile.attrib['maxQuantExperiment'] = "{}".format(category)

        eBiologicalSample = eInputFile.getparent()
        eBiologicalSample.attrib['category'] = "{}".format(category)
        eBiologicalSample.attrib['name'] = "{}".format(category)

        return(pBioSample)


    def getScaffold(selfs):
        xml = '''
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
        <DisplayThresholds id="thresh" minimumPeptideCount="1"
            peptideProbability="0.99" proteinProbability="0.96"/>
        <Export type="sf3"/>
    </Experiment>
</Scaffold>
'''
        pxml = etree.parse(StringIO(xml))
        return(pxml)


    def run(self):

        xml = self.getScaffold()
        eExperiment = xml.find('/Experiment')
        eFastaDatabase = xml.find('/Experiment/FastaDatabase')
        print(eFastaDatabase)
        eFastaDatabase.attrib['path'] = "{}".format(self.fasta)

        eExperiment.append(self.getBiologicalSample(1))
        eExperiment.append(self.getBiologicalSample(2))
        eExperiment.append(self.getBiologicalSample(3))
        eExperiment.append(self.getBiologicalSample(3))
        eExperiment.append(self.getBiologicalSample(3))


        #print(etree.tostring(xml, pretty_print=True, xml_declaration=True, method='xml', encoding="UTF-8"))

        xml.write('/dev/stdout' ,   pretty_print=True, xml_declaration=True,  method='xml', encoding="UTF-8")

if __name__ == "__main__":

    driver = FgczMaxQuantScaffold()
    driver.run()

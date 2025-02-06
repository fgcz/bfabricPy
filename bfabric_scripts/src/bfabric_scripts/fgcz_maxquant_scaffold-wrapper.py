#!/usr/bin/env python3
#
# Copyright (C) 2019 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#   Jonas Grossmann <jg@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#
# see also:
# https://fgcz-svn.uzh.ch/repos/fgcz/stable/bfabric/sgeworker/bin/fgcz_sge_maxquant_scaffold_A255.bash


import os
import sys
from lxml import etree
import yaml
from io import StringIO
from optparse import OptionParser

# import unittest


class FgczMaxQuantScaffold:
    """
    input:

    """

    config = None
    scratchdir = None
    fasta = None
    samples = None

    def __init__(self, yamlfilename=None, zipfilename=None) -> None:
        if not os.path.isfile(zipfilename):
            print(f"ERROR: no such file '{zipfilename}'")
            sys.exit(1)

        self.zipfilename = zipfilename
        with open(yamlfilename) as f:
            content = f.read()

        self.config = yaml.load(content, Loader=yaml.FullLoader)

        try:
            self.fasta = os.path.basename(
                self.config["application"]["parameters"]["/fastaFiles/FastaFileInfo/fastaFilePath"]
            )
        except:
            raise

        L = [value for values in self.config["application"]["input"].values() for value in values]

        self.samples = list(map(lambda x: os.path.basename(x).replace(".raw", ""), L))

    def getBiologicalSample(selfs, InputFile=None, category="***BASENAME***"):
        scaffold_BiologicalSample = """
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
        """

        pBioSample = etree.XML(scaffold_BiologicalSample)

        eInputFile = pBioSample.find("InputFile")

        if eInputFile is None:
            raise TypeError

        eInputFile.text = f"{InputFile}"
        eInputFile.attrib["maxQuantExperiment"] = f"{category}"

        eBiologicalSample = eInputFile.getparent()
        eBiologicalSample.attrib["category"] = f"{category}"
        eBiologicalSample.attrib["name"] = f"{category}"

        return pBioSample

    def getScaffold(selfs):
        xml = """
<Scaffold pathsep="/" version="Scaffold_4.8.9">
    <Experiment analyzeWithSubsetDB="false" analyzeWithTandem="false"
        annotateWithGOA="false" condenseDataWhileLoading="true"
        connectToNCBI="false"
        experimentDisplayType="Total Spectrum Count"
        name="fgcz_bfabric_scaffold"
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
"""
        pxml = etree.parse(StringIO(xml))
        # pxml = etree.XML(xml)
        return pxml

    def run(self) -> None:
        xml = self.getScaffold()
        eExperiment = xml.find("/Experiment")
        eFastaDatabase = xml.find("/Experiment/FastaDatabase")
        eFastaDatabase.attrib["path"] = f"{os.getcwd()}/{self.fasta}"

        for s in self.samples:
            eExperiment.extend(self.getBiologicalSample(category=s, InputFile=self.zipfilename))

        xml.write(
            "/dev/stdout",
            pretty_print=True,
            xml_declaration=True,
            method="xml",
            encoding="UTF-8",
        )


if __name__ == "__main__":
    parser = OptionParser(
        usage="usage: %prog -y <yaml formated config file> -z <zip file containing the MaxQuant results>",
        version="%prog 1.0",
    )

    parser.add_option(
        "-y",
        "--yaml",
        type="string",
        action="store",
        dest="yaml_filename",
        default="/Users/cp/WU199270.yaml ",
        help="config file.yaml",
    )

    parser.add_option(
        "-z",
        "--zip",
        type="string",
        action="store",
        dest="zip_filename",
        default="output-WU199270.zip",
        help="config file.yaml",
    )

    (options, args) = parser.parse_args()
    driver = FgczMaxQuantScaffold(yamlfilename=options.yaml_filename, zipfilename=options.zip_filename)
    driver.run()

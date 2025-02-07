#!/usr/bin/env python3
# Copyright (C) 2017, 2018 Functional Genomics Center Zurich ETHZ|UZH. All rights reserved.
#
# Authors:
#   Christian Panse <cp@fgcz.ethz.ch>
#
# Licensed under  GPL version 3
#

import os
import sys
from io import StringIO
from optparse import OptionParser
from pathlib import Path

import yaml
from lxml import etree

# import warnings

"""
requirements
- file system mounted via NFS

"""


class FgczMaxQuantConfig:
    """
    input:
      QEXACTIVE_2:
      - bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_01_Fetuin40fmol.raw
      - bfabric@fgczdata.fgcz-net.unizh.ch://srv/www/htdocs//p1946/Proteomics/QEXACTIVE_2/paolo_20150811_course/20150811_02_YPG1.raw
    output:

    """

    config = None
    scratchdir = None

    def __init__(self, config=None, scratch="/scratch/MAXQUANT/") -> None:
        if config:
            self.config = config
            self.scratchdir = Path(f"{scratch}/WU{self.config['job_configuration']['workunit_id']}")

            if not os.path.isdir(self.scratchdir):
                print(f"no scratch dir '{self.scratchdir}'.")
                # raise SystemError

    def generate_mqpar(self, xml_filename, xml_template) -> None:
        """PARAMETER"""
        for query, value in self.config["application"]["parameters"].items():
            element = xml_template.find(query)
            if element is not None:
                if value == "None":
                    element.text = ""
                elif query == "/parameterGroups/parameterGroup/variableModifications":
                    for a in value.split(","):
                        estring = etree.Element("string")
                        estring.text = a
                        element.extend(estring)
                    pass
                else:
                    print(f"replacing xpath expression {query} by {value}.")
                    element.text = value

        ecount = 0
        """ INPUT """
        for query, value in self.config["application"]["input"].items():
            for input in self.config["application"]["input"][query]:
                element = xml_template.find("/filePaths")
                if element is None:
                    raise TypeError

                host, file = input.split(":")

                print(f"{os.path.basename(input)}\t{file}")

                if not os.path.isfile(file):
                    print(f"'{file}' do not exists.")
                    # raise SystemError

                targetRawFile = f"{self.scratchdir}/{os.path.basename(input)}"

                if not os.path.islink(targetRawFile):
                    try:
                        os.symlink(file, targetRawFile)
                    except:
                        print(f"linking '{file}' failed.")

                estring = etree.Element("string")
                estring.text = targetRawFile
                element.extend(estring)

                element = xml_template.find("/experiments")
                if element is None:
                    raise TypeError

                estring = etree.Element("string")
                estring.text = f"{os.path.basename(input).replace('.raw', '').replace('.RAW', '')}"
                ecount += 1
                element.extend(estring)

                element = xml_template.find("/fractions")
                if element is None:
                    raise TypeError

                estring = etree.Element("short")
                estring.text = "32767"
                element.extend(estring)

                element = xml_template.find("/ptms")
                if element is None:
                    raise TypeError

                estring = etree.Element("boolean")
                estring.text = "false"
                element.extend(estring)

                element = xml_template.find("/paramGroupIndices")
                if element is None:
                    raise TypeError

                estring = etree.Element("int")
                estring.text = "0"
                element.extend(estring)

        # return(xml_template)
        xml_template.write(xml_filename)  # , pretty_print=True)

    def run(self) -> None:
        pass


mqpar_templ_xml = """<MaxQuantParams xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   <fastaFiles>
      <FastaFileInfo>
         <fastaFilePath>test.fasta</fastaFilePath>
         <identifierParseRule>>([^ ]*)</identifierParseRule>
         <descriptionParseRule>>(.*)</descriptionParseRule>
         <taxonomyParseRule></taxonomyParseRule>
         <variationParseRule></variationParseRule>
         <modificationParseRule></modificationParseRule>
         <taxonomyId></taxonomyId>
      </FastaFileInfo>
   </fastaFiles>
   <fastaFilesProteogenomics>
   </fastaFilesProteogenomics>
   <fastaFilesFirstSearch>
   </fastaFilesFirstSearch>
   <fixedSearchFolder></fixedSearchFolder>
   <andromedaCacheSize>350000</andromedaCacheSize>
   <advancedRatios>True</advancedRatios>
   <pvalThres>0.005</pvalThres>
   <neucodeRatioBasedQuantification>False</neucodeRatioBasedQuantification>
   <neucodeStabilizeLargeRatios>False</neucodeStabilizeLargeRatios>
   <rtShift>False</rtShift>
   <separateLfq>False</separateLfq>
   <lfqStabilizeLargeRatios>True</lfqStabilizeLargeRatios>
   <lfqRequireMsms>True</lfqRequireMsms>
   <decoyMode>revert</decoyMode>
   <boxCarMode>all</boxCarMode>
   <includeContaminants>True</includeContaminants>
   <maxPeptideMass>4600</maxPeptideMass>
   <epsilonMutationScore>True</epsilonMutationScore>
   <mutatedPeptidesSeparately>True</mutatedPeptidesSeparately>
   <proteogenomicPeptidesSeparately>True</proteogenomicPeptidesSeparately>
   <minDeltaScoreUnmodifiedPeptides>0</minDeltaScoreUnmodifiedPeptides>
   <minDeltaScoreModifiedPeptides>6</minDeltaScoreModifiedPeptides>
   <minScoreUnmodifiedPeptides>0</minScoreUnmodifiedPeptides>
   <minScoreModifiedPeptides>40</minScoreModifiedPeptides>
   <secondPeptide>True</secondPeptide>
   <matchBetweenRuns>True</matchBetweenRuns>
   <matchUnidentifiedFeatures>False</matchUnidentifiedFeatures>
   <matchBetweenRunsFdr>False</matchBetweenRunsFdr>
   <dependentPeptides>False</dependentPeptides>
   <dependentPeptideFdr>0</dependentPeptideFdr>
   <dependentPeptideMassBin>0</dependentPeptideMassBin>
   <dependentPeptidesBetweenRuns>False</dependentPeptidesBetweenRuns>
   <dependentPeptidesWithinExperiment>False</dependentPeptidesWithinExperiment>
   <dependentPeptidesWithinParameterGroup>False</dependentPeptidesWithinParameterGroup>
   <dependentPeptidesRestrictFractions>False</dependentPeptidesRestrictFractions>
   <dependentPeptidesFractionDifference>0</dependentPeptidesFractionDifference>
   <msmsConnection>False</msmsConnection>
   <ibaq>True</ibaq>
   <top3>False</top3>
   <independentEnzymes>False</independentEnzymes>
   <useDeltaScore>False</useDeltaScore>
   <splitProteinGroupsByTaxonomy>False</splitProteinGroupsByTaxonomy>
   <taxonomyLevel>Species</taxonomyLevel>
   <avalon>False</avalon>
   <nModColumns>3</nModColumns>
   <ibaqLogFit>True</ibaqLogFit>
   <razorProteinFdr>True</razorProteinFdr>
   <deNovoSequencing>False</deNovoSequencing>
   <deNovoVarMods>True</deNovoVarMods>
   <massDifferenceSearch>False</massDifferenceSearch>
   <isotopeCalc>False</isotopeCalc>
   <writePeptidesForSpectrumFile></writePeptidesForSpectrumFile>
   <intensityPredictionsFile>
   </intensityPredictionsFile>
   <minPepLen>7</minPepLen>
   <xPsmFdrInterProtein>0.05</xPsmFdrInterProtein>
   <xPsmFdrIntraProtein>0.01</xPsmFdrIntraProtein>
   <psmFdrMonolink>0.01</psmFdrMonolink>
   <psmFdrLooplink>0.01</psmFdrLooplink>
   <peptideFdr>0.01</peptideFdr>
   <proteinFdr>0.05</proteinFdr>
   <siteFdr>0.01</siteFdr>
   <minPeptideLengthForUnspecificSearch>8</minPeptideLengthForUnspecificSearch>
   <maxPeptideLengthForUnspecificSearch>25</maxPeptideLengthForUnspecificSearch>
   <useNormRatiosForOccupancy>True</useNormRatiosForOccupancy>
   <minPeptides>1</minPeptides>
   <minRazorPeptides>1</minRazorPeptides>
   <minUniquePeptides>0</minUniquePeptides>
   <useCounterparts>False</useCounterparts>
   <advancedSiteIntensities>True</advancedSiteIntensities>
   <customProteinQuantification>False</customProteinQuantification>
   <customProteinQuantificationFile></customProteinQuantificationFile>
   <minRatioCount>2</minRatioCount>
   <restrictProteinQuantification>True</restrictProteinQuantification>
   <restrictMods>
      <string>Oxidation (M)</string>
      <string>Acetyl (Protein N-term)</string>
   </restrictMods>
   <matchingTimeWindow>0.7</matchingTimeWindow>
   <alignmentTimeWindow>20</alignmentTimeWindow>
   <numberOfCandidatesMultiplexedMsms>25</numberOfCandidatesMultiplexedMsms>
   <numberOfCandidatesMsms>15</numberOfCandidatesMsms>
   <compositionPrediction>0</compositionPrediction>
   <quantMode>1</quantMode>
   <massDifferenceMods>
   </massDifferenceMods>
   <mainSearchMaxCombinations>200</mainSearchMaxCombinations>
   <writeMsScansTable>True</writeMsScansTable>
   <writeMsmsScansTable>True</writeMsmsScansTable>
   <writePasefMsmsScansTable>True</writePasefMsmsScansTable>
   <writeAccumulatedPasefMsmsScansTable>True</writeAccumulatedPasefMsmsScansTable>
   <writeMs3ScansTable>True</writeMs3ScansTable>
   <writeAllPeptidesTable>True</writeAllPeptidesTable>
   <writeMzRangeTable>True</writeMzRangeTable>
   <writeMzTab>False</writeMzTab>
   <disableMd5>False</disableMd5>
   <connected>False</connected>
   <cacheBinInds>True</cacheBinInds>
   <etdIncludeB>False</etdIncludeB>
   <complementaryTmtCollapseNplets>True</complementaryTmtCollapseNplets>
   <connectedScore0>0.8</connectedScore0>
   <connectedScore1>0.9</connectedScore1>
   <connectedScore2>1</connectedScore2>
   <stackPeaks>False</stackPeaks>
   <ms2PrecursorShift>0</ms2PrecursorShift>
   <complementaryIonPpm>20</complementaryIonPpm>
   <variationParseRule></variationParseRule>
   <variationMode>none</variationMode>
   <useSeriesReporters>False</useSeriesReporters>
   <name>session1</name>
   <maxQuantVersion>1.6.2.3</maxQuantVersion>
   <tempFolder></tempFolder>
   <pluginFolder></pluginFolder>
   <numThreads>48</numThreads>
   <emailAddress></emailAddress>
   <smtpHost></smtpHost>
   <emailFromAddress></emailFromAddress>
   <fixedCombinedFolder></fixedCombinedFolder>
   <fullMinMz>-1.79769313486232E+308</fullMinMz>
   <fullMaxMz>1.79769313486232E+308</fullMaxMz>
   <sendEmail>False</sendEmail>
   <ionCountIntensities>False</ionCountIntensities>
   <verboseColumnHeaders>False</verboseColumnHeaders>
   <calcPeakProperties>False</calcPeakProperties>
   <showCentroidMassDifferences>False</showCentroidMassDifferences>
   <showIsotopeMassDifferences>False</showIsotopeMassDifferences>
   <useDotNetCore>False</useDotNetCore>
   <filePaths>
   </filePaths>
   <experiments>
   </experiments>
   <fractions>
   </fractions>
   <ptms>
   </ptms>
   <paramGroupIndices>
   </paramGroupIndices>
   <parameterGroups>
      <parameterGroup>
         <msInstrument>0</msInstrument>
         <maxCharge>7</maxCharge>
         <minPeakLen>2</minPeakLen>
         <useMs1Centroids>False</useMs1Centroids>
         <useMs2Centroids>False</useMs2Centroids>
         <cutPeaks>True</cutPeaks>
         <gapScans>1</gapScans>
         <minTime>NaN</minTime>
         <maxTime>NaN</maxTime>
         <matchType>MatchFromAndTo</matchType>
         <intensityDetermination>0</intensityDetermination>
         <centroidMatchTol>8</centroidMatchTol>
         <centroidMatchTolInPpm>True</centroidMatchTolInPpm>
         <centroidHalfWidth>35</centroidHalfWidth>
         <centroidHalfWidthInPpm>True</centroidHalfWidthInPpm>
         <valleyFactor>1.4</valleyFactor>
         <isotopeValleyFactor>1.2</isotopeValleyFactor>
         <advancedPeakSplitting>False</advancedPeakSplitting>
         <intensityThreshold>0</intensityThreshold>
         <labelMods>
            <string></string>
         </labelMods>
         <lcmsRunType>Standard</lcmsRunType>
         <reQuantify>True</reQuantify>
         <lfqMode>1</lfqMode>
         <lfqSkipNorm>False</lfqSkipNorm>
         <lfqMinEdgesPerNode>3</lfqMinEdgesPerNode>
         <lfqAvEdgesPerNode>6</lfqAvEdgesPerNode>
         <lfqMaxFeatures>100000</lfqMaxFeatures>
         <neucodeMaxPpm>0</neucodeMaxPpm>
         <neucodeResolution>0</neucodeResolution>
         <neucodeResolutionInMda>False</neucodeResolutionInMda>
         <neucodeInSilicoLowRes>False</neucodeInSilicoLowRes>
         <fastLfq>True</fastLfq>
         <lfqRestrictFeatures>False</lfqRestrictFeatures>
         <lfqMinRatioCount>2</lfqMinRatioCount>
         <maxLabeledAa>0</maxLabeledAa>
         <maxNmods>5</maxNmods>
         <maxMissedCleavages>2</maxMissedCleavages>
         <multiplicity>1</multiplicity>
         <enzymeMode>0</enzymeMode>
         <complementaryReporterType>0</complementaryReporterType>
         <neucodeIntensityMode>0</neucodeIntensityMode>
         <fixedModifications>
            <string>Carbamidomethyl (C)</string>
         </fixedModifications>
         <enzymes>
            <string>Trypsin/P</string>
         </enzymes>
         <enzymesFirstSearch>
         </enzymesFirstSearch>
         <enzymeModeFirstSearch>0</enzymeModeFirstSearch>
         <useEnzymeFirstSearch>False</useEnzymeFirstSearch>
         <useVariableModificationsFirstSearch>False</useVariableModificationsFirstSearch>
         <variableModifications>
         </variableModifications>
         <useMultiModification>False</useMultiModification>
         <multiModifications>
         </multiModifications>
         <isobaricLabels>
         </isobaricLabels>
         <neucodeLabels>
         </neucodeLabels>
         <variableModificationsFirstSearch>
         </variableModificationsFirstSearch>
         <hasAdditionalVariableModifications>False</hasAdditionalVariableModifications>
         <additionalVariableModifications>
         </additionalVariableModifications>
         <additionalVariableModificationProteins>
         </additionalVariableModificationProteins>
         <doMassFiltering>True</doMassFiltering>
         <firstSearchTol>20</firstSearchTol>
         <mainSearchTol>4.5</mainSearchTol>
         <searchTolInPpm>True</searchTolInPpm>
         <isotopeMatchTol>2</isotopeMatchTol>
         <isotopeMatchTolInPpm>True</isotopeMatchTolInPpm>
         <isotopeTimeCorrelation>0.6</isotopeTimeCorrelation>
         <theorIsotopeCorrelation>0.6</theorIsotopeCorrelation>
         <checkMassDeficit>True</checkMassDeficit>
         <recalibrationInPpm>True</recalibrationInPpm>
         <intensityDependentCalibration>False</intensityDependentCalibration>
         <minScoreForCalibration>70</minScoreForCalibration>
         <matchLibraryFile>False</matchLibraryFile>
         <libraryFile></libraryFile>
         <matchLibraryMassTolPpm>0</matchLibraryMassTolPpm>
         <matchLibraryTimeTolMin>0</matchLibraryTimeTolMin>
         <matchLabelTimeTolMin>0</matchLabelTimeTolMin>
         <reporterMassTolerance>NaN</reporterMassTolerance>
         <reporterPif>NaN</reporterPif>
         <filterPif>False</filterPif>
         <reporterFraction>NaN</reporterFraction>
         <reporterBasePeakRatio>NaN</reporterBasePeakRatio>
         <timsHalfWidth>0</timsHalfWidth>
         <timsStep>0</timsStep>
         <timsResolution>0</timsResolution>
         <timsMinMsmsIntensity>0</timsMinMsmsIntensity>
         <timsRemovePrecursor>True</timsRemovePrecursor>
         <timsIsobaricLabels>False</timsIsobaricLabels>
         <timsCollapseMsms>True</timsCollapseMsms>
         <crosslinkSearch>False</crosslinkSearch>
         <crossLinker></crossLinker>
         <minPepLenXl>0</minPepLenXl>
         <minMatchXl>0</minMatchXl>
         <minPairedPepLenXl>6</minPairedPepLenXl>
         <crosslinkOnlyIntraProtein>False</crosslinkOnlyIntraProtein>
         <crosslinkMaxMonoUnsaturated>0</crosslinkMaxMonoUnsaturated>
         <crosslinkMaxMonoSaturated>0</crosslinkMaxMonoSaturated>
         <crosslinkMaxDiUnsaturated>0</crosslinkMaxDiUnsaturated>
         <crosslinkMaxDiSaturated>0</crosslinkMaxDiSaturated>
         <crosslinkUseSeparateFasta>False</crosslinkUseSeparateFasta>
         <crosslinkCleaveModifications>
         </crosslinkCleaveModifications>
         <crosslinkFastaFiles>
         </crosslinkFastaFiles>
         <crosslinkMode>PeptidesWithCleavedLinker</crosslinkMode>
      </parameterGroup>
   </parameterGroups>
   <msmsParamsArray>
      <msmsParams>
         <Name>FTMS</Name>
         <MatchTolerance>20</MatchTolerance>
         <MatchToleranceInPpm>True</MatchToleranceInPpm>
         <DeisotopeTolerance>7</DeisotopeTolerance>
         <DeisotopeToleranceInPpm>True</DeisotopeToleranceInPpm>
         <DeNovoTolerance>10</DeNovoTolerance>
         <DeNovoToleranceInPpm>True</DeNovoToleranceInPpm>
         <Deisotope>True</Deisotope>
         <Topx>12</Topx>
         <TopxInterval>100</TopxInterval>
         <HigherCharges>True</HigherCharges>
         <IncludeWater>True</IncludeWater>
         <IncludeAmmonia>True</IncludeAmmonia>
         <DependentLosses>True</DependentLosses>
         <Recalibration>False</Recalibration>
      </msmsParams>
      <msmsParams>
         <Name>ITMS</Name>
         <MatchTolerance>0.5</MatchTolerance>
         <MatchToleranceInPpm>False</MatchToleranceInPpm>
         <DeisotopeTolerance>0.15</DeisotopeTolerance>
         <DeisotopeToleranceInPpm>False</DeisotopeToleranceInPpm>
         <DeNovoTolerance>0.25</DeNovoTolerance>
         <DeNovoToleranceInPpm>False</DeNovoToleranceInPpm>
         <Deisotope>False</Deisotope>
         <Topx>8</Topx>
         <TopxInterval>100</TopxInterval>
         <HigherCharges>True</HigherCharges>
         <IncludeWater>True</IncludeWater>
         <IncludeAmmonia>True</IncludeAmmonia>
         <DependentLosses>True</DependentLosses>
         <Recalibration>False</Recalibration>
      </msmsParams>
      <msmsParams>
         <Name>TOF</Name>
         <MatchTolerance>40</MatchTolerance>
         <MatchToleranceInPpm>True</MatchToleranceInPpm>
         <DeisotopeTolerance>0.01</DeisotopeTolerance>
         <DeisotopeToleranceInPpm>False</DeisotopeToleranceInPpm>
         <DeNovoTolerance>0.02</DeNovoTolerance>
         <DeNovoToleranceInPpm>False</DeNovoToleranceInPpm>
         <Deisotope>True</Deisotope>
         <Topx>10</Topx>
         <TopxInterval>100</TopxInterval>
         <HigherCharges>True</HigherCharges>
         <IncludeWater>True</IncludeWater>
         <IncludeAmmonia>True</IncludeAmmonia>
         <DependentLosses>True</DependentLosses>
         <Recalibration>False</Recalibration>
      </msmsParams>
      <msmsParams>
         <Name>Unknown</Name>
         <MatchTolerance>0.5</MatchTolerance>
         <MatchToleranceInPpm>False</MatchToleranceInPpm>
         <DeisotopeTolerance>0.15</DeisotopeTolerance>
         <DeisotopeToleranceInPpm>False</DeisotopeToleranceInPpm>
         <DeNovoTolerance>0.25</DeNovoTolerance>
         <DeNovoToleranceInPpm>False</DeNovoToleranceInPpm>
         <Deisotope>False</Deisotope>
         <Topx>8</Topx>
         <TopxInterval>100</TopxInterval>
         <HigherCharges>True</HigherCharges>
         <IncludeWater>True</IncludeWater>
         <IncludeAmmonia>True</IncludeAmmonia>
         <DependentLosses>True</DependentLosses>
         <Recalibration>False</Recalibration>
      </msmsParams>
   </msmsParamsArray>
</MaxQuantParams>
"""

if __name__ == "__main__":
    parser = OptionParser(usage="usage: %prog -y <yaml formated config file>", version="%prog 1.0")

    parser.add_option(
        "-y",
        "--yaml",
        type="string",
        action="store",
        dest="yaml_filename",
        default=None,
        help="config file.yaml",
    )

    parser.add_option(
        "-x",
        "--xml",
        type="string",
        action="store",
        dest="xml_filename",
        default=None,
        help="MaxQuant mqpar xml parameter filename.",
    )

    parser.add_option(
        "-t",
        "--xmltemplate",
        type="string",
        action="store",
        dest="xml_template_filename",
        default=None,
        help="MaxQuant mqpar template xml parameter filename.",
    )

    (options, args) = parser.parse_args()

    if not os.path.isfile(options.yaml_filename):
        print(f"ERROR: no such file '{options.yaml_filename}'")
        sys.exit(1)
    try:
        with open(options.yaml_filename) as f:
            job_config = yaml.safe_load(f)

        if options.xml_template_filename is None:
            try:
                mqpartree = etree.parse(StringIO(mqpar_templ_xml))
            except:
                raise
        else:
            with open(options.xml_template_filename) as f:
                mqpartree = etree.parse(f)

        MQC = FgczMaxQuantConfig(config=job_config, scratch="d:/scratch/")
        output = MQC.generate_mqpar(options.xml_filename, xml_template=mqpartree)

    except:
        print("ERROR: exit 1")
        raise


import unittest

"""
python3 -m unittest fgcz_maxquant_wrapper.py
"""


class TestFgczMaxQuantConfig(unittest.TestCase):
    def test_xml(self) -> None:
        input_WU181492_yaml = """
application:
  input:
    QEXACTIVEHFX_1:
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_018_S185295_178_Control.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_010_S185303_151_HF-iDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_019_S185297_90_Control.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_015_S185304_234_HF-iDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_013_S185305_145_HF-iDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_005_S185302_204_HF-iDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_003_S185299_226_Control_rep.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_004_S185301_152_HF-iDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_020_S185296_180_Control.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_009_S185306_143_HF-mutiDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_021_S185308_148_HF-mutiDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_008_S185307_218_HF-iDCM.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_014_S185300_27_Control.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_016_S185298_95_Control.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_006_S185293_29_Control.raw
    - bfabric@fgcz-ms.uzh.ch://srv/www/htdocs//p2621/Proteomics/QEXACTIVEHFX_1/lkunz_20181002_OID4854_all/20181002_011_S185294_88_Control.raw
  output:
  - bfabric@fgcz-ms.uzh.ch:/srv/www/htdocs//p2621/bfabric/Proteomics/MaxQuant/2018/2018-10/2018-10-26//workunit_181492//927691.zip
  parameters:
    /enzymes/string: Trypsin/P
    /fastaFiles/FastaFileInfo/fastaFilePath: /srv/www/htdocs/FASTA/fgcz_9606_reviewed_cnl_contaminantNoHumanCont_20161209.fasta
    /numThreads: '48'
    /parameterGroups/parameterGroup/fixedModifications/string: Carbamidomethyl (C)
    /parameterGroups/parameterGroup/variableModifications: Acetyl (Protein N-term),Oxidation
      (M),Deamidation (NQ)
    Rmd: QCReport.Rmd
  protocol: scp
job_configuration:
  executable: /home/bfabric/sgeworker/bin/fgcz_sge_maxquant_linux.bash
  external_job_id: !!python/long '64924'
  input:
    QEXACTIVEHFX_1:
    - resource_id: 720998
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720998
    - resource_id: 720997
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720997
    - resource_id: 720996
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720996
    - resource_id: 720995
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720995
    - resource_id: 720994
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720994
    - resource_id: 720993
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720993
    - resource_id: 720992
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720992
    - resource_id: 720991
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720991
    - resource_id: 720990
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720990
    - resource_id: 720989
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720989
    - resource_id: 720988
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720988
    - resource_id: 720987
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720987
    - resource_id: 720986
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720986
    - resource_id: 720985
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720985
    - resource_id: 720984
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720984
    - resource_id: 720983
      resource_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-resource.html?resourceId=720983
  output:
    protocol: scp
    resource_id: 927691
    ssh_args: -o StrictHostKeyChecking=no -2 -l bfabric -x
  stderr:
    protocol: file
    resource_id: 927692
    url: /home/bfabric/sgeworker/logs/workunitid-181492_resourceid-927691.err
  stdout:
    protocol: file
    resource_id: 927693
    url: /home/bfabric/sgeworker/logs/workunitid-181492_resourceid-927691.out
  workunit_id: 181492
  workunit_url: https://fgcz-bfabric.uzh.ch/bfabric/userlab/show-workunit.html?workunitId=181492

        """

        job_config = yaml.safe_load(input_WU181492_yaml)
        mqpartree = etree.parse(StringIO(mqpar_templ_xml))

        MQC = FgczMaxQuantConfig(config=job_config)
        MQC.generate_mqpar("/tmp/output.xml", xml_template=mqpartree)

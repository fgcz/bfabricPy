#!/usr/bin/python2.7

# Creates scaffoldBatch driver for a list of dat files.
# usage: python create_scaffold_xml_driver.py scaffoldOutputFilePath.sf3 myDat1.dat myDat2.dat...



import fileinput
import os.path
import sys
import getopt
import urllib

#import xml.dom.minidom as minidom
from lxml import etree 

svninfo = """
$HeadURL: http://fgcz-svn.uzh.ch/repos/fgcz/stable/proteomics/bin/fgcz_scaffold_create_xml_driver.py $
$Id: fgcz_scaffold_create_xml_driver.py 7552 2015-06-30 11:21:26Z cpanse $
$Date: 2015-06-30 13:21:26 +0200 (Tue, 30 Jun 2015) $
"""


scaffold_xsd = """
<xs:schema attributeFormDefault="unqualified" elementFormDefault="qualified" xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Scaffold">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Experiment">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="FastaDatabase" maxOccurs="1" minOccurs="1">
                <xs:complexType>
                  <xs:simpleContent>
                    <xs:extension base="xs:string">
                      <xs:attribute type="xs:string" name="id"/>
                      <xs:attribute type="xs:string" name="path"/>
                      <xs:attribute type="xs:string" name="databaseAccessionRegEx"/>
                      <xs:attribute type="xs:string" name="databaseDescriptionRegEx"/>
                      <xs:attribute type="xs:string" name="decoyProteinRegEx"/>
                    </xs:extension>
                  </xs:simpleContent>
                </xs:complexType>
              </xs:element>
              <xs:element name="BiologicalSample" maxOccurs="100" minOccurs="1">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element type="xs:string" name="InputFile" maxOccurs="1500" minOccurs="1"/>
                  </xs:sequence>
                  <xs:attribute type="xs:string" name="database"/>
                  <xs:attribute type="xs:boolean" name="analyzeAsMudpit"/>
                  <xs:attribute type="xs:string" name="name"/>
                  <xs:attribute type="xs:string" name="category"/>
                </xs:complexType>
              </xs:element>
              <xs:element name="DisplayThresholds">
                <xs:complexType>
                  <xs:simpleContent>
                    <xs:extension base="xs:string">
                      <xs:attribute type="xs:string" name="name"/>
                      <xs:attribute type="xs:string" name="id"/>
                      <xs:attribute type="xs:float" name="proteinProbability"/>
                      <xs:attribute type="xs:byte" name="minimumPeptideCount"/>
                      <xs:attribute type="xs:float" name="peptideProbability"/>
                    </xs:extension>
                  </xs:simpleContent>
                </xs:complexType>
              </xs:element>
              <xs:element name="Export">
                <xs:complexType>
                  <xs:simpleContent>
                    <xs:extension base="xs:string">
                      <xs:attribute type="xs:string" name="type"/>
                      <xs:attribute type="xs:string" name="thresholds"/>
                      <xs:attribute type="xs:string" name="path"/>
                    </xs:extension>
                  </xs:simpleContent>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
            <xs:attribute type="xs:string" name="name"/>
            <xs:attribute type="xs:boolean" name="analyzeWithTandem"/>
            <xs:attribute type="xs:boolean" name="connectToNCBI"/>
            <xs:attribute type="xs:boolean" name="condenseDataWhileLoading"/>
            <xs:attribute type="xs:boolean" name="annotateWithGOA"/>
            <xs:attribute type="xs:string" name="unimodFile"/>
            <xs:attribute type="xs:boolean" name="highMassAccuracyScoring"/>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

# MAIN

def main(argv):
    """
    """

    tandemOption = 'false'
    mudPitOption = 'false'
    gelcmsOption = 'false'
    workunitId = None
    qModel = None
    qModelSpace = ['iTRAQ_4-Plex', 'iTRAQ_8-Plex']
    try:
        opts, args = getopt.getopt(argv, "m:x:q:w:g:", ["mudpit=", "xtandem=", "qmodel=", "workunit=", "gelcms="])
    except getopt.GetoptError:
        print "{0} --mudpit=[TRUE|FALSE] --xtandem=[TRUE|FALSE] --gelcms=[TRUE|FALSE]".format(sys.argv[0])
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-m", "--mudpit"):
            if arg in ['TRUE', 'true', 'True']:
                mudPitOption='true'
        elif opt in ("-x", "--xtandem"):
            if arg in ['TRUE', 'true', 'True']:
                tandemOption='true'
        elif opt in ("-g", "--gelcms"):
            if arg in ['TRUE', 'true', 'True']:
                gelcmsOption='true'
        elif opt in ("-w", "--workunit"):
                workunitId=arg
        elif opt in ("-q", "--qmodel"):
                if arg in qModelSpace:
                    qModel = arg
                else:
                    sys.stderr.write("Warning: QuantitativeModel is not available. possible options are:\n\t{0}.".format(qModelSpace))
                    qModel=None

    #PARAMETERS for Testing:
    inputFiles=[]
    scaffoldOutputFilePath = "{0}/scaffold.sf3".format(os.getcwd())

    for line in fileinput.input(files=['-']):
        f = os.path.basename(line.rstrip('\n'))
        f = os.path.abspath(f)
        if os.path.isfile(f):
            inputFiles.append(f)
        else:
            print ("ERROR: {0} file is not available on the system".format(f))

    #PARAMETERS 

    # get descriptions and meta data from the first mascot dat file
    i = 0
    for line in fileinput.input(inputFiles[0]):
        if line.startswith("DB="):
            fastaId = line.split("=")[1].strip()
        if line.startswith("release="): 
            fastaDBName = line.split("=")[1].strip()
            fastaDBPath = "/imports/share/fgcz/db/{0}".format(fastaDBName)
            if not os.path.isfile(fastaDBPath): 
                sys.exit("ERROR: {0} does not exist:".format(fastaDBPath))
        if line.startswith("INSTRUMENT="):
            instrumentName = line.split("=")[1].strip()
        if line.startswith("COM="):
            searchTitle = line.split("=")[1].strip()    
        # stop after 1500 lines
        i+=1
        if i > 1500: 
            break

    # TODO(cp): should be workuntit ID
    experimentName = "Experiment: {0}".format(searchTitle)
    if workunitId is not None:
        experimentName = "Experiment: FGCZ B-Fabric workunit id {0}".format(workunitId)

    # begin creating scaffold xml driver
    root = etree.Element("Scaffold")
    root.append(etree.Comment("This driver has been created using: {}".format(svninfo)))

    Experiment = etree.SubElement(root, "Experiment")
    experimentDetails = [("name", experimentName), 
        ("analyzeWithTandem", tandemOption),
        ("connectToNCBI", 'false'), 
        ("condenseDataWhileLoading", 'true'), 
        ("annotateWithGOA", 'true'), 
        ("unimodFile", ''), 
        ("highMassAccuracyScoring", 'true')]

    for item in experimentDetails:
        Experiment.set(*item)

    FastaDatabase = etree.SubElement(Experiment, "FastaDatabase")

    # ("databaseAccessionRegEx", '>([^ ]*)'),
    # ("databaseAccessionRegEx", '>([^), ( ]*)'), 
    # ("databaseAccessionRegEx", ">([^ ]*)")
    fastaDatabaseDetails = [("id", fastaId), 
        ("path", fastaDBPath), 
        ("databaseAccessionRegEx",   ">([^ ]*)"),
        ("databaseDescriptionRegEx", ">[^ ]* (.*)"), 
        ("decoyProteinRegEx", ".*REV_")]

    map(lambda item: FastaDatabase.set(*item), fastaDatabaseDetails)

    BiologicalSample = etree.SubElement(Experiment, "BiologicalSample")

    biologicalSampleDetails = [("database", fastaId), 
        ("analyzeAsMudpit", mudPitOption), 
        ("name", searchTitle), 
        ("category", searchTitle)]

    map(lambda item: BiologicalSample.set(*item), biologicalSampleDetails)

    for file in inputFiles:
        InputFile = etree.SubElement(BiologicalSample, "InputFile")
        InputFile.text = file

    DisplayThresholds = etree.SubElement(Experiment, "DisplayThresholds")
    displayThresholdsDetails = [("name", "DTs"), 
        ("id", "thresh"), 
        ("proteinProbability", '0.95'), 
        ("minimumPeptideCount", '2'), 
        ("peptideProbability", '0.95')]

    map(lambda item: DisplayThresholds.set(*item), displayThresholdsDetails)
    
    if qModel == "iTRAQ_4-Plex":
        qModelString = """
<QuantitativeModel type="iTRAQ 4-Plex">
                <QuantitativeSample category="Reference" description=""
                    name="Quant 1" primary="true" reporter="iTRAQ-114"/>
                <QuantitativeSample category="" description=""
                    name="Quant 2" primary="false" reporter="iTRAQ-115"/>
                <QuantitativeSample category="" description=""
                    name="Quant 3" primary="false" reporter="iTRAQ-116"/>
                <QuantitativeSample category="" description=""
                    name="Quant 4" primary="false" reporter="iTRAQ-117"/>
                <PurityCorrection>0.000,0.01000,0.925,0.0630,0.00200
0.000,0.0200,0.919,0.0600,0.001000
0.000,0.0300,0.920,0.0490,0.001000
0.001000,0.0400,0.920,0.0380,0.001000</PurityCorrection>
            </QuantitativeModel>
            """
        BiologicalSample.append(etree.fromstring(qModelString))
    elif qModel == "iTRAQ_8-Plex":
        qModelString = """
<QuantitativeModel type="iTRAQ 8-Plex">
                <QuantitativeSample category="Reference" description=""
                    name="Quant 1" primary="true" reporter="iTRAQ-113"/>
                <QuantitativeSample category="category 1" description=""
                    name="Quant 2" primary="false" reporter="iTRAQ-114"/>
                <QuantitativeSample category="category 2" description=""
                    name="Quant 3" primary="false" reporter="iTRAQ-115"/>
                <QuantitativeSample category="category 3" description=""
                    name="Quant 4" primary="false" reporter="iTRAQ-116"/>
                <QuantitativeSample category="category 4" description=""
                    name="Quant 5" primary="false" reporter="iTRAQ-117"/>
                <QuantitativeSample category="category 5" description=""
                    name="Quant 6" primary="false" reporter="iTRAQ-118"/>
                <QuantitativeSample category="category 6" description=""
                    name="Quant 7" primary="false" reporter="iTRAQ-119"/>
                <QuantitativeSample category="category 7" description=""
                    name="Quant 8" primary="false" reporter="iTRAQ-121"/>
                <PurityCorrection>0.000,0.000,0.929,0.0689,0.00220
0.000,0.00940,0.930,0.0590,0.00160
0.000,0.0188,0.931,0.0490,0.001000
0.000,0.0282,0.932,0.0390,0.000700
0.000600,0.0377,0.933,0.0288,0.000
0.000900,0.0471,0.933,0.0188,0.000
0.00140,0.0566,0.933,0.00870,0.000
0.000,0.000,0.000,0.000,0.000</PurityCorrection>
            </QuantitativeModel>
"""
        BiologicalSample.append(etree.fromstring(qModelString))
    else:
        pass


    Export = etree.SubElement(Experiment, "Export")
    exportDetails = [("type", "sf3"), 
        ("thresholds", "thresh"), 
        ("path", scaffoldOutputFilePath)]

    map(lambda item: Export.set(*item), exportDetails)

    tree = etree.ElementTree(root)
    # optional: tree.write("filename.xml")

    rough_string = etree.tostring(root, pretty_print=True)

    # TODO(cp): xsd check would be nice to have
    try:
        schema = etree.XMLSchema(etree.XML(scaffold_xsd))
    except:
        print "build xsd schema failed."
        raise

    # double check if xml string can be parsed
    parser = etree.XMLParser(remove_blank_text=True, schema=schema)
    try:
        xmlScaffoldDriver = etree.fromstring(rough_string, parser)
    except ValueError, e:
        print "error: scaffold driver xml can not be parsed"
        print e
        sys.exit(1)

    # print results - write to /dev/stdout 
    print  etree.tostring(xmlScaffoldDriver, pretty_print=True)
   
if __name__ == "__main__":
    main(sys.argv[1:])

# branch *bfabric10* wsdl python3 package -- suds-py3

This package connects the [bfabric](https://fgcz-bfabric.uzh.ch/bfabric/) system to the [python](https://www.python.org/) and [R](https://cran.r-project.org/) world while providing a JSON and REST interface using [Flask](https://www.fullstackpython.com).
 The [bfabricShiny](https://github.com/cpanse/bfabricShiny) R package is an extension and provides code snippets and sample implementation for a seamless R shiny bfabric integration.
For more advanced users the *bfabricPy* package also provides a powerful query interface on the command-line though using the provided scripts.


![bfabricPy-read](https://user-images.githubusercontent.com/4901987/65025926-db77c900-d937-11e9-8c92-f2412d6793ee.gif)

## Requirements

- install current stable Debian Linux release (any current BSD like or Microsoft OS will do)

- install the python3 package as follow:

```{bash}
git clone git@github.com:cpanse/bfabricPy.git  \
  && cd bfabricPy \
  && git checkout bfabric10
```

## Install

```{bash}
python3 setup.py sdist && sudo pip3 install dist/bfabric-0.10.*.tar.gz
```


## Configuration

```{bash}
cat ~/.bfabricrc.py 
_WEBBASE="https://fgcz-bfabric-test.uzh.ch/bfabric"
_LOGIN="yourBfabricLogin"
_PASSWD='yourBfabricWebPassword'
```

## CheatSheet

### Read

```{bash}
bfabric_list.py storage
bfabric_list.py application
```

Simple database query examples

```{bash}
bfabric_list.py user login cpanse
bfabric_list.py project id 3000
bfabric_list.py workunit id 199387
bfabric_list.py sample name autoQC4L
bfabric_list.py workunit status running
bfabric_list.py workunit status pending
bfabric_list.py workunit status failed

# list empty resources
bfabric_list.py resource filechecksum d41d8cd98f00b204e9800998ecf8427e
```

call the `python3` interpreter and enter

```{py}
import bfabric

B = bfabric.Bfabric()

user = B.read_object(endpoint = 'user', obj={'login': 'cpanse'})
resource = B.read_object(endpoint = 'resource', obj={'id': 550327 })
```

### Command line code snippets

remove pending workunits from the past
```{bash} 
 bfabric_list.py workunit status pending \
   | awk '$2~/cpanse/&&$3~/2015/{print $1}'
   | fgcz_bfabric_delete_workunits.py 
```

find empty resource files in bfabric
```{bash}
bfabric_list.py resource filechecksum `md5sum < /dev/null | cut -c-32` \
  | cat -n \
  | tail
```

## Examples

### bash script generated by the yaml wrapper creator / submitter

externaljobid-45939_executableid-15312.bash listing:

```bash
#!/bin/bash
#
# $HeadURL: http://fgcz-svn.uzh.ch/repos/scripts/trunk/linux/bfabric/apps/python/README.md $
# $Id: README.md 2535 2016-10-24 08:49:17Z cpanse $
# Christian Panse <cp@fgcz.ethz.ch> 2007-2015

# Grid Engine Parameters
#$ -q PRX@fgcz-c-071
#$ -e /home/bfabric/sgeworker/logs/workunitid-134923_resourceid-203236.err
#$ -o /home/bfabric/sgeworker/logs/workunitid-134923_resourceid-203236.out


set -e
set -o pipefail

export EXTERNALJOBID=45938
export RESSOURCEID_OUTPUT=203238
export RESSOURCEID_STDOUT_STDERR="203237 203238"
export OUTPUT="bfabric@fgczdata.fgcz-net.unizh.ch:/srv/www/htdocs//p1000/bfabric/Proteomics/gerneric_yaml/2015/2015-09/2015-09-02//workunit_134923//203236.zip"

# job configuration set by B-Fabrics wrapper_creator executable
_OUTPUT=`echo $OUTPUT | cut -d"," -f1`
test $? -eq 0 && _OUTPUTHOST=`echo $_OUTPUT | cut -d":" -f1`
test $? -eq 0 && _OUTPUTPATH=`echo $_OUTPUT | cut -d":" -f2`
test $? -eq 0 && _OUTPUTPATH=`dirname $_OUTPUTPATH`
test $? -eq 0 && ssh $_OUTPUTHOST "mkdir -p $_OUTPUTPATH"

if [ $? -eq 1 ];
then
    echo "writting to output url failed!";
    exit 1;
fi

cat > /tmp/yaml_config.$$ <<EOF
application:
  input:
    mascot_dat:
    - bfabric@fgcz-s-018.uzh.ch//usr/local/mascot/:/data/20150807/F221967.dat
    - bfabric@fgcz-s-018.uzh.ch//usr/local/mascot/:/data/20150807/F221973.dat
  output:
  - bfabric@fgczdata.fgcz-net.unizh.ch:/srv/www/htdocs//p1000/bfabric/Proteomics/gerneric_yaml/2015/2015-09/2015-09-02//workunit_134923//203236.zip
  parameters:
    gelcms: 'true'
    mudpit: 'false'
    qmodel: None
    xtandem: 'false'
  protocol: scp
job_configuration:
  executable: /usr/local/fgcz/proteomics/bin/fgcz_scaffold.bash
  external_job_id: 45938
  input:
    mascot_dat:
    - 201919
    - 201918
  output:
    protocol: scp
    resource_id: 203238
    ssh_args: -o StrictHostKeyChecking=no -c arcfour -2 -l bfabric -x
  stderr:
    protocol: file
    resource_id: 203237
    url: /home/bfabric/sgeworker/logs/workunitid-134923_resourceid-203236.err
  stdout:
    protocol: file
    resource_id: 203238
    url: /home/bfabric/sgeworker/logs/workunitid-134923_resourceid-203236.out
  workunit_id: 134923

EOF

# debug / host statistics
hostname
uptime
echo $0
pwd

# run the application
test -f /tmp/yaml_config.$$ && /usr/local/fgcz/proteomics/bin/fgcz_scaffold.bash /tmp/yaml_config.$$

if [ $? -eq 0 ];
then
    /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID_OUTPUT
    /home/bfabric/.python/fgcz_bfabric_setExternalJobStatus_done.py $EXTERNALJOBID
else
    echo "application failed"
    /home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR $RESSOURCEID;
    exit 1;
fi


# Should be available also as zero byte files

/home/bfabric/.python/fgcz_bfabric_setResourceStatus_available.py $RESSOURCEID_STDOUT_STDERR

exit 0
```

### curl example

```{bash}
#!/bin/bash

query(){
  url=$1 \
  && curl \
    ${url} \
    -v \
    --header "Content-Type: text/xml;charset=UTF-8" \
    --header "SOAPAction: read" \
    -d '
  <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:end="http://endpoint.webservice.component.bfabric.org/">
     <soapenv:Header/>
     <soapenv:Body>
        <end:read>
           <parameters>
              <login>XXX</login>
              <password>XXX</password>
              <query>
                 <id>482</id>
              </query>
           </parameters>
        </end:read>
     </soapenv:Body>
  </soapenv:Envelope>'
}

for url in https://fgcz-bfabric.uzh.ch/bfabric/user?wsdl https://fgcz-bfabric-test.uzh.ch/bfabric/user?wsdl;
do 
  echo
  echo "==== ${url} === "
  query ${url}
done

echo $?
```


### Example usage

remove accidentally inserted mgf files

```
bfabric_list.py importresource \
  | grep mgf$ \
  | awk '{print $1}' \
  | tee /tmp/$$.log \
  | while read i; 
  do 
    bfabric_delete.py importresource $i ; 
  done
```


## Testing

```{sh}
cd bfabric/tests/ && python3 -m unittest discover; echo $?; cd -
```


## See also
- [FAQ](faq.md)
- [wsdl4BFabric](http://fgcz-intranet.uzh.ch/tiki-index.php?page=wsdl4BFabric) wiki page
- WSDL Interface to B-Fabric [endpoints](http://fgcz-bfabric.uzh.ch/bfabric/workunit?wsdl)


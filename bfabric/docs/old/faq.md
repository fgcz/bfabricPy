# FAQ

## Q: Howto upload a small file to bfabric?

by @gwhite-fgcz

```{py}
"""
this script saves a file 'ttt.py' in bfabric.
"""
import bfabric
import base64
import os

# given
filename = "ttt.py"

bf = bfabric.Bfabric()

app = bf.save_object('application',
    {'name': "dummy", "type": 'webapp', 'technologyid': 1, 'weburl': 'nirvana', 'description': 'this is a dummy application' })

print(app[0])
applicationid = app[0]._id

wu = bf.save_object('workunit', {'containerid':3000, 'name':'TEST', 'applicationid':applicationid})

print(wu[0])
workunitid = wu[0]._id

with open(filename, 'r') as f:
    content = f.read()

resource_base64 = base64.b64encode(content.encode())

res = bf.save_object('resource', {'base64': resource_base64, 'name': os.path.basename(filename), 'description': "some bla bla bla ...", 'workunitid': workunitid})
print(res[0])
resourceid = res[0]._id


# cleanup

rv = bf.delete_object('resource', resourceid)
print(rv[0])
rv = bf.delete_object('workunit', workunitid)
print(rv[0])
rv = bf.delete_object('application', applicationid)
print(rv[0])
```

![save_resource](https://user-images.githubusercontent.com/4901987/65670931-9abe3500-e046-11e9-91db-b9a443a95a54.gif)

## Q: Howto query for time and date - range query

by @gwhite-fgcz

range query are not possible with the current API design

whatsoever time format is as follow

```{py}
 # the timeformat bfabric understands
    _file_date = time.strftime("%FT%H:%M:%S-01:00",time.gmtime(int(_file_date)))
```

workaround fetch entire orders and filter later

```
import json
import bfabric
import datetime

try:
    with open('orders.json') as json_file:
        data = json.load(json_file)

except:
    bf = bfabric.Bfabric()
    rv = bf.read_object('order', {})

    data = list(map(lambda x: (x.customer._id, x.modified.year, x.modified.month, x.modified.day, x.servicetypename), rv))

    # cache data
    with open('orders.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True, indent=4)


lastyear = datetime.datetime.now() - datetime.timedelta(days=365)
for customerid, year, month, day, servicetypename in data:
    dt = datetime.datetime(year=year, month=month, day=day)
    if dt > lastyear:
        print ("{}\t{}\t{}".format(year, servicetypename, customerid))
```

KPI frequency table - returning `customerid`s

```{bash}
cp@fgcz-148:~ > python3 orders.py |awk '{print $NF}'|sort | uniq -c| awk '{print $1}'|sort |uniq -c|sort -gr | awk '{s+=$1*$2; print s"\t"$0}'
557         557 1
1091        267 2
1586        165 3
1946         90 4
2226         56 5
2532         51 6
2756         32 7
3026         30 9
3234         26 8
3384         15 10
3514         10 13
3640          9 14
3748          9 12
3836          8 11
3938          6 17
4028          6 15
4104          4 19
4168          4 16
4243          3 25
4306          3 21
4360          3 18
4448          2 44
4524          2 38
4594          2 35
4662          2 34
4724          2 31
4782          2 29
4830          2 24
4870          2 20
4938          1 68
5005          1 67
5067          1 62
5124          1 57
5174          1 50
5223          1 49
5269          1 46
5312          1 43
5348          1 36
5378          1 30
5406          1 28
5433          1 27
5534          1 101
```

## Q: SSL: CERTIFICATE_VERIFY_FAILED on MacOSX

by @cpanse

```
cp@fgcz-113:~ > bfabric_list.py storage
bfabricPy version 0.10.1 (2019-08-31) -- "suds-py3"
Copyright (C) 2019 Functional Genomics Center Zurich

<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1051)>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/urllib/request.py", line 1317, in do_open
    encode_chunked=req.has_header('Transfer-encoding'))
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/http/client.py", line 1229, in request
    self._send_request(method, url, body, headers, encode_chunked)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/http/client.py", line 1275, in _send_request
    self.endheaders(body, encode_chunked=encode_chunked)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/http/client.py", line 1224, in endheaders
    self._send_output(message_body, encode_chunked=encode_chunked)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/http/client.py", line 1016, in _send_output
    self.send(msg)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/http/client.py", line 956, in send
    self.connect()
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/http/client.py", line 1392, in connect
    server_hostname=server_hostname)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/ssl.py", line 412, in wrap_socket
    session=session
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/ssl.py", line 853, in _create
    self.do_handshake()
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/ssl.py", line 1117, in do_handshake
    self._sslobj.do_handshake()
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1051)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.7/bin/bfabric_list.py", line 61, in <module>
    res = bfapp.read_object(endpoint=endpoint, obj=query_obj)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/bfabric/bfabric.py", line 169, in read_object
    client = Client("".join((self.webbase, '/', endpoint, "?wsdl")), cache=None)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/client.py", line 111, in __init__
    self.wsdl = reader.open(url)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/reader.py", line 152, in open
    d = self.fn(url, self.options)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/wsdl.py", line 135, in __init__
    d = reader.open(url)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/reader.py", line 79, in open
    d = self.download(url)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/reader.py", line 95, in download
    fp = self.options.transport.open(Request(url))
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/transport/http.py", line 174, in open
    return HttpTransport.open(self, request)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/transport/http.py", line 63, in open
    return self.u2open(u2request)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages/suds/transport/http.py", line 119, in u2open
    return url.open(u2request, timeout=tm)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/urllib/request.py", line 525, in open
    response = self._open(req, data)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/urllib/request.py", line 543, in _open
    '_open', req)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/urllib/request.py", line 503, in _call_chain
    result = func(*args)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/urllib/request.py", line 1360, in https_open
    context=self._context, check_hostname=self._check_hostname)
  File "/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/urllib/request.py", line 1319, in do_open
    raise URLError(err)
urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1051)>
cp@fgcz-113:~ > cat .bfabricrc.py
#_WEBBASE="https://fgcz-bfabric-demo.uzh.ch/bfabric"
#_LOGIN="pfeeder"
#_PASSWD='dcf40f74250459c2a7110951e2472749'

_WEBBASE="https://fgcz-bfabric.uzh.ch/bfabric"
_LOGIN="cpanse"
_PASSWD='dcf40f74250459c2a7110951e2472749'

cp@fgcz-113:~ > bfabric_list.py storage
bfabricPy version 0.10.1 (2019-08-31) -- "suds-py3"
Copyright (C) 2019 Functional Genomics Center Zurich

5	admin	2014-04-04 07:19:17.162000+02:00	gStore
3	system	2014-04-04 07:18:55.803000+02:00	GeneralRepo
9	admin	2017-02-21 18:52:34.237000+01:00	Local Internal Storage
6	admin	2014-04-04 07:19:34.293000+02:00	Proteomics FASTA
4	admin	2013-12-04 13:02:09.308000+01:00	Mascot Repo
8	slavicad	2019-03-29 13:18:50.482000+01:00	gStore Reports
10	admin	2017-02-21 18:52:34.258000+01:00	Local External Storage
7	cpanse	2014-04-04 07:19:46.822000+02:00	gridEngineLog
11	schmidt	2018-02-18 18:38:13.271000+01:00	TIA Storage
2	system	2014-04-04 07:18:41.325000+02:00	PrxRepo
1	system	2014-04-04 07:18:13.915000+02:00	Developer Storage
--- number of query result items = 11 ---
--- query time = 0.25 seconds ---

cp@fgcz-113:~ >
```

solution:
[Once upon a time I stumbled with this issue. If you're using macOS go to Macintosh HD > Applications > Python3.6 folder (or whatever version of python you're using) > double click on "Install Certificates.command" file. :D](https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org)

## Q:Howto add a custom attribute to a sample?

```{py}
#!/usr/bin/env python3
# -*- coding: latin1 -*-

import sys
import os
import bfabric

"""
    customattribute[] =
      (xmlCustomAttribute){
         name = "Age0"
         value = "49"
         type = "String"
      },

"""
if __name__ == "__main__":
    print("this code is under construction.")
    bfapp = bfabric.Bfabric(verbose=False)

    res = bfapp.read_object(endpoint='sample', obj={'id': 206577})

    customattribute = res[0].customattribute
    customattribute.append({'name': "{}I".format(customattribute[len(customattribute)-1].name), 'value': '0'})

    res = bfapp.save_object(endpoint='sample', obj={'id': 206577, 'customattribute': customattribute})
    #res = bfapp.save_object(endpoint='sample', obj={'id': 206577, 'customattribute': [{'name': 'Age1', 'value': '0'}]})
    print(res[0])
```

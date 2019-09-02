# FAQ


## Q: SSL: CERTIFICATE_VERIFY_FAILED on MacOSX

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

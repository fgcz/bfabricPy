# B-Fabric Application WSDL Interface 
This is all about lsunching applications out of the B-Fabric system.

![bfabric.py UML](/images/classes_No_Name.png)


## INSTALL
requires: python suds linrary and drmaa for connecting to the grid sceduler
(https://pypi.python.org/pypi/suds)
### Linux Debian
```bash
apt-get install python-suds
```
    


## Configure
endpoints:
(http://fgcz-bfabric-demo.uzh.ch/bfabric/workunit?wsdl)

## Testing (on the demo system)
```bash
$ ./submit_executable.py -j 13668
$ ./wrapper_creator.py -j 13668
```


## See Also

(http://fgcz-intranet.uzh.ch/tiki-index.php?page=wsdl4BFabric)

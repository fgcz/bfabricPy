import xmlrpclib
import sys

proxy = xmlrpclib.ServerProxy("http://130.60.81.74:9999/")
print proxy.maxquant()

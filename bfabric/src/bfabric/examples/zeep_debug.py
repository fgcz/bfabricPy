from bfabric import BfabricAuth, BfabricClientConfig
from bfabric.bfabric import get_system_auth
import zeep
from copy import deepcopy
from lxml import etree

"""
Attempt to understand why Zeep does not correctly parse XML
* Problem 1: (minor) Zeep generates additional Null fields not available in XML, but likely (hypothetically) available in XSD
* Problem 2: (major) Zeep fails to parse <project id=5 ...> parameters in some users.

Effort:
[+] helpers.serialize_object is NOT the culprit, the parsed XMLResponse is already missing the values.
[-] Manipulating client.settings does not seem to affect the output

Intermediate conclusions:
* Both behaviours are most likely internal bugs of Zeep. Unfortunately, developer does not respond to issues at the moment.
"""


def full_query(auth: BfabricAuth, query: dict, includedeletableupdateable: bool = False) -> dict:
    thisQuery = deepcopy(query)
    thisQuery["includedeletableupdateable"] = includedeletableupdateable

    return {"login": auth.login, "password": auth.password.get_secret_value(), "query": thisQuery}


def read_zeep(wsdl, fullQuery, raw=True):
    client = zeep.Client(wsdl)
    with client.settings(strict=False, raw_response=raw):
        ret = client.service.read(fullQuery)
    if raw:
        return ret.content
    else:
        return ret


def read(
    auth: BfabricAuth,
    config: BfabricClientConfig,
    endpoint: str,
    query: dict,
    raw: bool = True,
):
    wsdl = "".join((config.base_url, "/", endpoint, "?wsdl"))
    fullQuery = full_query(auth, query)
    return read_zeep(wsdl, fullQuery, raw=raw)


bfconfig, bfauth = get_system_auth(config_env="TEST")

print("============== RAW ================")

rez = read(bfauth, bfconfig, "user", {"id": 9026}, raw=True)
root = etree.fromstring(rez)
print(etree.tostring(root, pretty_print=True).decode())

rez = read(bfauth, bfconfig, "user", {"id": 9026}, raw=False)

print("============== ORIG ================")
print(rez["user"][0]["project"])
print(rez["user"][0]["project"]["id"])

# trg = rez['project']
#
# print('============== ORIG ================')
# print(trg)
#
#
# print('============== SERIAL ================')
#
# print(zeep.helpers.serialize_object(trg, target_cls=dict))

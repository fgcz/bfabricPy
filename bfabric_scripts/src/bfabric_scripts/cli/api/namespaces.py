"""Namespace mappings for SOAP API type introspection."""

# Prefix -> URI mapping
NAMESPACES = {
    "xs": "http://www.w3.org/2001/XMLSchema",
    "bf": "http://endpoint.server.webservice.bfabric.org/",
}

# URI -> Prefix mapping (reverse lookup)
NAMESPACE_URIS = {uri: prefix for prefix, uri in NAMESPACES.items()}

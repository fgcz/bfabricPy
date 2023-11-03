#
#
# by WEW

import bfabric


class bfabricEncoder(json.JSONEncoder):
    """
    Implements json encoder for the Bfabric.print_json method
    """
    def default(self, o):
        try:
            return dict(o)
        except TypeError:
            pass
        else:
            return list(o)
        return JSONEncoder.default(self, o)


res = json.dumps(queryres, cls=bfabricEncoder, sort_keys=True, indent=2)


B = bfabric.Bfabric()


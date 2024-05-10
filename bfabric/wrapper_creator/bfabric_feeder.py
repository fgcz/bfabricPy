import hashlib
import os

from bfabric.bfabric_legacy import BfabricLegacy


class BfabricFeeder(BfabricLegacy):
    """
        this class is used for reporting 'resource' status
    """

    def report_resource(self, resourceid):
        """
        this function determines the 'md5 checksum', 'the file size',
        and set the status of the resource available.

        this is gonna executed on the storage host

        """
        res = self.read_object('resource', {'id': resourceid})[0]
        print (res)

        if not hasattr(res, 'storage'):
            return -1

        storage = self.read_object('storage', {'id': res.storage._id})[0]

        filename = "{0}/{1}".format(storage.basepath, res.relativepath)

        if os.path.isfile(filename):
            try:
                fmd5 = hashlib.md5(open(filename, 'rb').read()).hexdigest()
                print ("md5sum ({}) = {}".format(filename, fmd5))

                fsize = int(os.path.getsize(filename)) + 1
                print ("size ({}) = {}".format(filename, fsize))


                return self.save_object('resource', {'id': resourceid,
                                                 'size': fsize,
                                                 'status': 'available',
                                                 'filechecksum': fmd5})
            except:
                print ("computing md5 failed")
                # print ("{} {}".format(Exception, err))
                raise

        return self.save_object('resource', {'id': resourceid, 'status': 'failed'})

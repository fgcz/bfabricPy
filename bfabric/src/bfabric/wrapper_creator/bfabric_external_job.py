import json

from bfabric.bfabric_legacy import bfabricEncoder, BfabricLegacy


class BfabricExternalJob(BfabricLegacy):
    """
    ExternalJobs can use logging.
    if you have a valid externaljobid use this class instead of
    using Bfabric.


    TODO check if an external job id is provided
    """

    externaljobid = None

    def __init__(self, login=None, password=None, externaljobid=None):
        super().__init__(login, password)
        if not externaljobid:
            print("Error: no externaljobid provided.")
            raise
        else:
            self.externaljobid = externaljobid

        print(f"BfabricExternalJob externaljobid={self.externaljobid}")

    def logger(self, msg):
        if self.externaljobid:
            super().save_object("externaljob", {"id": self.externaljobid, "logthis": str(msg)})
        else:
            print(str(msg))

    def save_object(self, endpoint, obj, debug=None):
        res = super().save_object(endpoint, obj, debug)
        jsonres = json.dumps(res, cls=bfabricEncoder, sort_keys=True, indent=2)
        self.logger("saved " + endpoint + "=" + str(jsonres))
        return res

    def get_workunitid_of_externaljob(self):
        print(f"DEBUG get_workunitid_of_externaljob self.externaljobid={self.externaljobid}")
        res = self.read_object(endpoint="externaljob", obj={"id": self.externaljobid})[0]
        print(res)
        print("DEBUG END")
        workunit_id = None
        try:
            workunit_id = res.cliententityid
            print(f"workunitid={workunit_id}")
        except:
            pass
        return workunit_id

    def get_application_name(self):
        workunitid = self.get_workunitid_of_externaljob()
        if workunitid is None:
            raise ValueError("no workunit available for the given externaljobid.")
        workunit = self.read_object(endpoint="workunit", obj={"id": workunitid})[0]
        if workunit is None:
            raise ValueError("ERROR: no workunit available for the given externaljobid.")
        assert isinstance(workunit._id, int)
        application = self.read_object("application", obj={"id": workunit.application._id})[0]
        return application.name.replace(" ", "_")

    def get_executable_of_externaljobid(self):
        """
        It takes as input an `externaljobid` and fetches the the `executables`
        out of the bfabric system using wsdl into a file.
        returns a list of executables.

        todo: this function should check if base64 is provided or
        just a program.
        """
        workunitid = self.get_workunitid_of_externaljob()
        if workunitid is None:
            return None

        executables = list()
        for executable in self.read_object(endpoint="executable", obj={"workunitid": workunitid}):
            if hasattr(executable, "base64"):
                executables.append(executable)

        return executables if len(executables) > 0 else None

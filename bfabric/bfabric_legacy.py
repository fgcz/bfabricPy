from __future__ import annotations
import base64
import json
import os
import sys
from pprint import pprint
from typing import Any

import yaml
from suds.client import Client
from suds.wsdl import Service

from bfabric import BfabricConfig
from bfabric.bfabric_config import BfabricAuth, read_config


class BfabricLegacy:
    """B-Fabric python3 module
    Implements read and save object methods for B-Fabric wsdl interface
    """

    def warning(self, msg) -> None:
        sys.stderr.write(f"\033[93m{msg}\033[0m\n")

    def __init__(
        self,
        login: str = None,
        password: str = None,
        base_url: str = None,
        externaljobid=None,
        config_path: str = None,
        config_env: str = None,
        optional_auth: bool = False,
        verbose: bool = False,
    ) -> None:
        """
        :param login:           Login string for overriding config file
        :param password:        Password for overriding config file
        :param base_url:        Base url of the BFabric server for overriding config file
        :param externaljobid:   ?
        :param config_path:     Path to the config file, in case it is different from default
        :param config_env:      Which config environment to use. Can also specify via environment variable or use
           default in the config file (at your own risk)
        :param optional_auth:   Whether authentification is optional. If yes, missing authentification will be ignored,
           otherwise an exception will be raised
        :param verbose:         Verbosity (TODO: resolve potential redundancy with logger)
        """
        self.verbose = verbose

        self.cl = {}
        self.verbose = False
        self.query_counter = 0

        # Get default path config file path
        config_path = config_path or os.path.normpath(os.path.expanduser("~/.bfabricpy.yml"))

        # TODO: Convert to an exception when this branch becomes main
        config_path or os.path.normpath(os.path.expanduser("~/.bfabricrc.py"))
        if os.path.isfile(config_path):
            self.warning(
                "WARNING! The old .bfabricrc.py was found in the home directory. Delete and make sure to use the new .bfabricpy.yml"
            )

        # Use the provided config data from arguments instead of the file
        if not os.path.isfile(config_path):
            self.warning("could not find '.bfabricpy.yml' file in home directory.")
            self.config = BfabricConfig(base_url=base_url)
            self.auth = BfabricAuth(login=login, password=password)

        # Load config from file, override some of the fields with the provided ones
        else:
            config, auth = read_config(config_path, config_env=config_env, optional_auth=optional_auth)
            self.config = config.with_overrides(base_url=base_url)
            if (login is not None) and (password is not None):
                self.auth = BfabricAuth(login=login, password=password)
            elif (login is None) and (password is None):
                self.auth = auth
            else:
                raise OSError("Must provide both username and password, or neither.")

        if not self.config.base_url:
            raise ValueError("base server url missing")
        if not optional_auth:
            if not self.auth or not self.auth.login or not self.auth.password:
                raise ValueError("Authentification not initialized but required")

            msg = f"\033[93m--- base_url {self.config.base_url}; login; {self.auth.login} ---\033[0m\n"
            sys.stderr.write(msg)

        if self.verbose:
            pprint(self.config)

    def read_object(self, endpoint, obj, page=1, plain=False, idonly=False):
        """
        A generic method which can connect to any endpoint, e.g., workunit, project, order,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains all the attributes of the endpoint
        for the "query".
        """
        return self._perform_request(
            endpoint=endpoint, method="read", plain=plain, params=dict(query=obj, idonly=idonly, page=page)
        )

    def readid_object(self, endpoint, obj, page=1, plain=False):
        """
        A generic method which can connect to any endpoint, e.g., workunit, project, order,
        externaljob, etc, and returns the object with the requested id.
        obj is a python dictionary which contains only the id of the endpoint for the "query".
        """
        return self._perform_request(endpoint=endpoint, method="readid", plain=plain, params=dict(query=obj, page=page))

    def save_object(self, endpoint, obj, debug=None):
        """
        same as read_object above but uses the save method.
        """
        return self._perform_request(endpoint=endpoint, method="save", plain=debug is not None, params={endpoint: obj})

    def checkandinsert_object(self, endpoint, obj, debug=None):
        """
        wsdl method to check iff dependencies are fulfilled
        """
        # TODO This method was changed a while ago to use the "save"endpoint, which makes it functionally identical
        #      to the save_object method. Check if this was intended.
        return self._perform_request(endpoint=endpoint, method="save", plain=debug is not None, params={endpoint: obj})

    def delete_object(self, endpoint, id=None, debug=None):
        """
        same as read_object above but uses the delete method.
        """
        return self._perform_request(endpoint=endpoint, method="delete", plain=debug is not None, params=dict(id=id))

    def upload_file(self, filename, workunitid):
        with open(filename, "rb") as f:
            content = f.read()

        resource_base64 = base64.b64encode(content).decode()

        res = self.save_object(
            "resource",
            {
                "base64": resource_base64,
                "name": os.path.basename(filename),
                "description": "base64 encoded file",
                "workunitid": workunitid,
            },
        )

        return res

    def _get_service(self, endpoint: str) -> Service:
        """Returns a `suds.client.Service` object for the given endpoint name."""
        if endpoint not in self.cl:
            self.cl[endpoint] = Client(f"{self.config.base_url}/{endpoint}?wsdl", cache=None)
        return self.cl[endpoint].service

    def _perform_request(self, endpoint: str, method: str, plain: bool, params: dict[str, Any]) -> Any:
        """Performs a request to the given endpoint and returns the result."""
        self.query_counter += 1
        request_params = dict(login=self.auth.login, password=self.auth.password, **params)
        service = self._get_service(endpoint=endpoint)
        response = getattr(service, method)(request_params)
        if plain:
            return response
        elif getattr(response, "entitiesonpage", None) == 0:
            return []
        return getattr(response, endpoint)

    @staticmethod
    def print_json(queryres=None) -> None:
        """
        This method prints the query result as returned by ``read_object`` in JSON format.

        Parameter
        ---------

        queryres : the object returned by ``read_object`` method.
        """
        if queryres is None:
            raise TypeError(
                "print_json() missing 1 required positional argument: please provide the output from read_object as parameter to print_json"
            )

        res = json.dumps(queryres, cls=bfabricEncoder, sort_keys=True, indent=2)
        print(res)

    @staticmethod
    def print_yaml(queryres=None) -> None:
        """
        This method prints the query result as returned by ``read_object`` in YAML format.

        Parameter
        ---------

        queryres : the object returned by ``read_object`` method.
        """
        if queryres is None:
            raise TypeError(
                "print_yaml() missing 1 required positional argument: please provide the output from read_object as parameter to print_yaml"
            )

        res_json = json.dumps(queryres, cls=bfabricEncoder, sort_keys=True)
        res = yaml.dump(res_json, default_flow_style=False, encoding=None, default_style=None)
        print(res)

    def get_sampleid(self, resourceid=None):
        """
        determines the sample_id  of a given resource_id.
        it performs a recursive dfs.
        TODO(cp): check if the method should be implemented using a stack

        :param resourceid:
        :return: (int, int)
        """

        assert isinstance(resourceid, int)

        try:
            resource = self.read_object("resource", obj={"id": resourceid})[0]
        except:
            return None

        try:
            workunit = self.read_object(endpoint="workunit", obj={"id": resource.workunit._id})[0]
            return self.get_sampleid(resourceid=int(workunit.inputresource[0]._id))
        except:
            self.warning(f"fetching sampleid of resource.workunitid = {resource.workunit._id} failed.")
            return None


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

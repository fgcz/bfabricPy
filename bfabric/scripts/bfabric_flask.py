#!/usr/bin/env python3
"""
This script is thought to be used as a
Rest SOAP proxy.
In particular, it connects R shiny to https://bfabric.org


run as pfeeder
FLASK_APP=$(which bfabric_flask.py) flask run --host=0.0.0.0 

Christian Panse <cp@fgcz.ethz.ch>
Christian Trachsel
Marco Schmid

2016-07-05 1700
2017-05-11
2019-10-16 adapted to bfabric10
2022-02-04 adaptation to start flask by Debian's systemd
2023-05-08 use https if certified ssh keys are available


useful commands when using the debian package:

systemctl status bfabric-flask-prx.service

journalctl -u bfabric-flask-prx

journalctl -u bfabric-flask-prx -S -1h

systemctl restart bfabric-flask-prx.service

Of note, do not forget rerun the flask service after modification!
"""
from __future__ import annotations
import os
import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

from bfabric.bfabric2 import Bfabric
from bfabric.bfabric_config import BfabricAuth


if "BFABRICPY_CONFIG_ENV" not in os.environ:
    # Set the environment to the name of the PROD config section to use
    os.environ["BFABRICPY_CONFIG_ENV"] = "TEST"

DEFAULT_LOGGER_NAME = "bfabric13_flask"

logger = logging.getLogger(DEFAULT_LOGGER_NAME)
app = Flask(__name__)
client = Bfabric.from_config(auth=None, verbose=True)


def get_request_auth(request_data: dict[str, Any]) -> BfabricAuth:
    """Extracts the login and password from a JSON request body. Assumes it has been filtered beforehand."""
    webservicepassword = request_data["webservicepassword"].replace("\t", "")
    login = request_data["login"]
    return BfabricAuth(login=login, password=webservicepassword)


@app.errorhandler(Exception)
def handle_unknown_exception(e: Exception) -> Response:
    """Handles exceptions which are not handled by a more specific handler."""
    logger.error("Unknown exception", exc_info=e)
    return jsonify({"error": f"unknown exception occurred: {e}"})


@app.errorhandler(json.JSONDecodeError)
def handle_json_decode_error(e: json.JSONDecodeError) -> Response:
    """Handles JSON decode errors."""
    logger.error("JSON decode error", exc_info=e)
    return jsonify({"error": "could not parse JSON request content"})


class InvalidRequestContent(RuntimeError):
    """Raised when the request content is invalid."""

    def __init__(self, missing_fields: list[str]) -> None:
        super().__init__(f"missing fields: {missing_fields}")


@app.errorhandler(InvalidRequestContent)
def handle_invalid_request_content(e: InvalidRequestContent) -> Response:
    """Handles invalid request content errors."""
    logger.error("Invalid request content", exc_info=e)
    return jsonify({"error": f"invalid request content: {e}"})


def get_fields(required_fields: list[str], optional_fields: dict[str, Any]) -> dict[str, Any]:
    """Extracts fields from a JSON request body. All `required_fields` must be present, or an error will be raised
    indicating the missing fields. The optional fields are filled with the default values if not present.
    :param required_fields: list of required fields
    :param optional_fields: dictionary of optional fields with default values
    :return: dictionary of all field values, if all required fields are present
    """
    available_fields = request.json.keys()
    missing_fields = set(required_fields) - set(available_fields)
    if missing_fields:
        raise InvalidRequestContent(sorted(missing_fields))
    else:
        required_values = {field: request.json[field] for field in required_fields}
        optional_values = {field: request.json.get(field, default) for field, default in optional_fields.items()}
        return {**required_values, **optional_values}


@app.route("/read", methods=["POST"])
def read() -> Response:
    """Reads data from a particular B-Fabric endpoint matching a query."""
    params = get_fields(
        required_fields=["endpoint", "login", "webservicepassword"],
        optional_fields={"query": {}, "page_offset": 0, "page_max_results": 100},
    )
    query = params["query"]
    page_offset = params["page_offset"]
    page_max_results = params["page_max_results"]
    endpoint = params["endpoint"]
    auth = get_request_auth(params)

    logger.info(f"'{auth.login}' /read {page_offset=}, {page_max_results=}, {query=}")
    try:
        with client.with_auth(auth):
            client.print_version_message()
            res = client.read(
                endpoint=endpoint,
                obj=query,
                offset=page_offset,
                max_results=page_max_results,
            )
        logger.info(f"'{auth.login}' login success query {query} ...")
    except Exception:
        logger.exception(f"'{auth.login}' query failed ...")
        return jsonify({"status": "jsonify failed: bfabric python module."})

    try:
        return jsonify({"res": res.to_list_dict()})
    except Exception:
        logger.exception(f"'{auth.login}' query failed ...")
        return jsonify({"status": "jsonify failed"})


@app.route("/save", methods=["POST"])
def save() -> Response:
    """Saves data to a particular B-Fabric endpoint."""
    params = get_fields(required_fields=["endpoint", "query", "login", "webservicepassword"], optional_fields={})
    endpoint = params["endpoint"]
    query = params["query"]
    auth = get_request_auth(params)

    try:
        with client.with_auth(auth):
            res = client.save(endpoint=endpoint, obj=query)
        logger.info(f"'{auth.login}' login success save method ...")
    except Exception:
        logger.exception(f"save method failed for login {auth.login}.")
        return jsonify({"status": "jsonify failed: bfabric python module."})

    try:
        return jsonify({"res": res.to_list_dict()})
    except Exception:
        return jsonify({"status": "jsonify failed"})


@app.route("/add_resource", methods=["POST"])
def add_resource() -> Response:
    """Adds a resource to a workunit."""
    params = get_fields(
        required_fields=[
            "name",
            "workunitdescription",
            "containerid",
            "applicationid",
            "base64",
            "resourcename",
            "login",
            "webservicepassword",
        ],
        optional_fields={},
    )
    auth = get_request_auth(params)

    # Save the workunit
    with client.with_auth(auth):
        res = client.save(
            "workunit",
            {
                "name": params["name"],
                "description": params["workunitdescription"],
                "containerid": params["containerid"],
                "applicationid": params["applicationid"],
            },
        ).to_list_dict()
    logger.info(res)

    workunit_id = res[0]["id"]
    logger.info(f"workunit_id = {workunit_id}")

    with client.with_auth(auth):
        client.save(
            "resource",
            {
                "base64": params["base64"],
                "name": params["resourcename"],
                "workunitid": workunit_id,
            },
        )
        client.save("workunit", {"id": workunit_id, "status": "available"})

    return jsonify(dict(workunit_id=workunit_id))


# @app.route("/add_dataset/<int:containerid>", methods=["GET", "POST"])
# def add_dataset(containerid):
#    try:
#        queue_content = json.loads(request.data)
#    except:
#        return jsonify({"error": "could not get POST content."})
#
#    try:
#        obj = {}
#        obj["name"] = "autogenerated dataset by http://fgcz-s-028.uzh.ch:8080/queue_generator/"
#        obj["containerid"] = containerid
#        obj["attribute"] = [
#            {"name": "File Name", "position": 1, "type": "String"},
#            {"name": "Path", "position": 2},
#            {"name": "Position", "position": 3},
#            {"name": "Inj Vol", "position": 4, "type": "numeric"},
#            {"name": "ExtractID", "position": 5, "type": "extract"},
#        ]
#
#        obj["item"] = list()
#
#        for idx in range(0, len(queue_content)):
#            obj["item"].append(
#                {
#                    "field": map(
#                        lambda x: {
#                            "attributeposition": x + 1,
#                            "value": queue_content[idx][x],
#                        },
#                        range(0, len(queue_content[idx])),
#                    ),
#                    "position": idx + 1,
#                }
#            )
#
#            print(obj)
#
#    except:
#        return jsonify({"error": "composing bfabric object failed."})
#
#    try:
#        res = bfapp.save_object(endpoint="dataset", obj=obj)[0]
#        print("added dataset {} to bfabric.".format(res._id))
#        return jsonify({"id": res._id})
#
#    except:
#        print(res)
#        return jsonify({"error": "beaming dataset to bfabric failed."})


# @app.route("/zip_resource_of_workunitid/<int:workunitid>", methods=["GET"])
# def get_zip_resources_of_workunit(workunitid):
#    res = map(
#        lambda x: x.relativepath,
#        bfapp.read_object(endpoint="resource", obj={"workunitid": workunitid}),
#    )
#    print(res)
#    res = filter(lambda x: x.endswith(".zip"), res)
#    return jsonify(res)

# @app.route("/addworkunit", methods=["GET", "POST"])
# def add_workunit():
#    appid = request.args.get("appid", None)
#    pid = request.args.get("pid", None)
#    rname = request.args.get("rname", None)
#
#    try:
#        content = json.loads(request.data)
#        # print content
#    except:
#        return jsonify({"error": "could not get POST content.", "appid": appid})
#
#    resource_base64 = content["base64"]
#    # base64.b64encode(content)
#    print(resource_base64)
#
#    return jsonify({"rv": "ok"})


def setup_logger_prod(name: str = DEFAULT_LOGGER_NAME, address: tuple[str, int] = ("fgcz-ms.uzh.ch", 514)) -> None:
    """Sets up the production logger."""
    syslog_handler = logging.handlers.SysLogHandler(address=address)
    formatter = logging.Formatter("%(name)s %(message)s")
    syslog_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(syslog_handler)
    return logger


def setup_logger_debug(name: str = DEFAULT_LOGGER_NAME) -> None:
    """Sets up the debug logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger


def main() -> None:
    """Starts the server, auto-detecting production mode if SSL keys are present."""
    ssl_key_pub = Path("/etc/ssl/fgcz-host.pem")
    ssl_key_priv = Path("/etc/ssl/private/fgcz-host_key.pem")
    if ssl_key_pub.exists() and ssl_key_priv.exists():
        setup_logger_prod()
        app.run(
            debug=False,
            host="0.0.0.0",
            port=5001,
            ssl_context=(
                str(ssl_key_pub),
                str(ssl_key_priv),
            ),
        )
    else:
        setup_logger_debug()
        app.run(debug=False, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
This script is thought to be used as a
Rest SOAP proxy.
In particular, it connects R shiny to https://bfabric.org

Christian Panse <cp@fgcz.ethz.ch>
Christian Trachsel
Marco Schmid

2016-07-05 1700
2017-05-11
2019-10-16 adapted to bfabric10
2022-02-04 adaptation to start flask by Debian's systemd
2023-05-08 use https if certified ssh keys are available


useful commands when using the debian package:
(NOTE: This will need to be improved in the future)

systemctl status bfabric-flask-prx.service

journalctl -u bfabric-flask-prx

journalctl -u bfabric-flask-prx -S -1h

systemctl restart bfabric-flask-prx.service

Of note, do not forget rerun the flask service after modification!
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from flask import Flask, Response, jsonify, request
from loguru import logger

from bfabric import Bfabric, BfabricAuth
from bfabric.rest.token_data import get_raw_token_data

if "BFABRICPY_CONFIG_ENV" not in os.environ:
    # Set the environment to the name of the PROD config section to use
    os.environ["BFABRICPY_CONFIG_ENV"] = "TEST"


app = Flask(__name__)
client = Bfabric.connect(include_auth=False)


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
    logger.debug(e.doc)
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
    with client.with_auth(auth):
        client._log_version_message()
        res = client.read(
            endpoint=endpoint,
            obj=query,
            offset=page_offset,
            max_results=page_max_results,
        )
    logger.info(f"'{auth.login}' login success query {query} ...")

    return jsonify({"res": res.to_list_dict()})


@app.route("/save", methods=["POST"])
def save() -> Response:
    """Saves data to a particular B-Fabric endpoint."""
    params = get_fields(
        required_fields=["endpoint", "query", "login", "webservicepassword"],
        optional_fields={},
    )
    endpoint = params["endpoint"]
    query = params["query"]
    auth = get_request_auth(params)

    with client.with_auth(auth):
        res = client.save(endpoint=endpoint, obj=query)
    logger.info(f"'{auth.login}' login success save method ...")

    return jsonify({"res": res.to_list_dict()})


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


@app.route("/config/remote_base_url", methods=["GET"])
def get_remote_base_url() -> Response:
    """Returns the remote base URL, which is useful to verify we are testing against the right endpoint."""
    return jsonify({"remote_base_url": client.config.base_url})


@app.route("/validate_token", methods=["POST"])
def validate_token() -> Response:
    """Validates a token and returns the token data.

    This endpoint is not really necessary since it proxies a REST endpoint, but is added here for consistency to avoid
    shiny apps having to interface with two different APIs.
    """
    params = get_fields(required_fields=["token"], optional_fields={})
    token_data = get_raw_token_data(base_url=client.config.base_url, token=params["token"])
    return jsonify(token_data)


def main() -> None:
    """Starts the server, for development.
    Please use a WSGI server (e.g. gunicorn) and always use SSL in production!
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", type=str)
    parser.add_argument("--port", default=5000, type=int)
    args = parser.parse_args()
    app.run(debug=False, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

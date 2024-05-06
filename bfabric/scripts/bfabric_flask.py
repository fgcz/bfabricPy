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

import json
import logging
import logging.handlers
from os.path import exists
from typing import Any

from flask import Flask, Response, jsonify, request

import bfabric
from bfabric import bfabric2
from bfabric.bfabric_config import BfabricAuth

DEFAULT_LOGGER_NAME = "bfabric11_flask"


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


logger = logging.getLogger(DEFAULT_LOGGER_NAME)
app = Flask(__name__)
client = bfabric2.Bfabric.from_config("TEST", auth=None, verbose=True)


def get_request_auth(request_data: dict[str, Any]) -> BfabricAuth | None:
    try:
        webservicepassword = request_data["webservicepassword"].replace("\t", "")
        login = request_data["login"]
        return BfabricAuth(login=login, password=webservicepassword)
    except (TypeError, KeyError, IndexError):
        return None


@app.route("/read", methods=["POST"])
def read() -> Response:
    try:
        # required fields
        endpoint = request.json["endpoint"]
        query = request.json["query"]
        auth = get_request_auth(request.json)

        # optional fields
        page_offset = request.json.get("page_offset", 0)
        page_max_results = request.json.get("page_max_results", 100)
        idonly = request.json.get("idonly", False)
    except json.JSONDecodeError:
        return jsonify({"error": "could not parse JSON request content"})
    except (KeyError, IndexError):
        return jsonify({"error": "could not get required POST content."})

    # check if authenticated
    if not auth:
        return jsonify({"error": "could not get login and password."})

    logger.info(f"'{auth.login}' /read {page_offset=}, {page_max_results=}, {idonly=}")
    try:
        with client.with_auth(auth):
            client.print_version_message()
            res = client.read(
                endpoint=endpoint,
                obj=query,
                # TODO offset
                max_results=page_max_results,
                readid=idonly,
            )
        logger.info("'{}' login success query {} ...".format(auth.login, request.json["query"]))
    except Exception:
        logger.exception("'{}' query failed ...".format(auth.login))
        return jsonify({"status": "jsonify failed: bfabric python module."})

    try:
        return jsonify({"res": res.to_list_dict()})
    except Exception:
        logger.exception("'{}' query failed ...".format(auth.login))
        return jsonify({"status": "jsonify failed"})


@app.route("/save", methods=["POST"])
def save() -> Response:
    try:
        # required fields
        endpoint = request.json["endpoint"]
        query = request.json["query"]
        auth = get_request_auth(request.json)
    except json.JSONDecodeError:
        return jsonify({"error": "could not parse JSON request content"})
    except (KeyError, IndexError):
        return jsonify({"error": "could not get required POST content."})

    # check if authenticated
    if not auth:
        return jsonify({"error": "could not get login and password."})

    try:
        with client.with_auth(auth):
            res = client.save(endpoint=endpoint, obj=query)
        logger.info("'{}' login success save method ...".format(auth.login))
    except Exception:
        logger.exception("save method failed for login {}.".format(auth.login))
        return jsonify({"status": "jsonify failed: bfabric python module."})

    try:
        return jsonify({"res": res.to_list_dict()})
    except Exception:
        return jsonify({"status": "jsonify failed"})


@app.route("/add_resource", methods=["POST"])
def add_resource() -> Response:
    try:
        name = request.json["name"]
        description = request.json["workunitdescription"]
        container_id = request.json["containerid"]
        application_id = request.json["applicationid"]
        queue_content = request.json["base64"]
        resource_name = request.json["resourcename"]
        auth = get_request_auth(request.json)
    except json.JSONDecodeError:
        logger.exception("failed: could not get POST content")
        return jsonify({"error": "could not get POST content."})
    except (KeyError, IndexError):
        logger.exception("failed: could not get required POST content.")
        return jsonify({"error": "could not get required POST content."})

    # check if authenticated
    if not auth:
        return jsonify({"error": "could not get login and password."})

    # Save the workunit
    with client.with_auth(auth):
        res = client.save(
            "workunit",
            {
                "name": name,
                "description": description,
                "containerid": container_id,
                "applicationid": application_id,
            },
        ).to_list_dict()
    logger.info(res)

    workunit_id = res[0]["id"]
    logger.info(f"workunit_id = {workunit_id}")

    with client.with_auth(auth):
        client.save(
            "resource",
            {
                "base64": queue_content,
                "name": resource_name,
                "workunitid": workunit_id,
            },
        )
        client.save("workunit", {"id": workunit_id, "status": "available"})

    return jsonify(dict(workunit_id=workunit_id))


@app.route("/add_dataset/<int:containerid>", methods=["GET", "POST"])
def add_dataset(containerid):
    try:
        queue_content = json.loads(request.data)
    except:
        return jsonify({"error": "could not get POST content."})

    try:
        obj = {}
        obj["name"] = "autogenerated dataset by http://fgcz-s-028.uzh.ch:8080/queue_generator/"
        obj["containerid"] = containerid
        obj["attribute"] = [
            {"name": "File Name", "position": 1, "type": "String"},
            {"name": "Path", "position": 2},
            {"name": "Position", "position": 3},
            {"name": "Inj Vol", "position": 4, "type": "numeric"},
            {"name": "ExtractID", "position": 5, "type": "extract"},
        ]

        obj["item"] = list()

        for idx in range(0, len(queue_content)):
            obj["item"].append(
                {
                    "field": map(
                        lambda x: {
                            "attributeposition": x + 1,
                            "value": queue_content[idx][x],
                        },
                        range(0, len(queue_content[idx])),
                    ),
                    "position": idx + 1,
                }
            )

            print(obj)

    except:
        return jsonify({"error": "composing bfabric object failed."})

    try:
        res = bfapp.save_object(endpoint="dataset", obj=obj)[0]
        print("added dataset {} to bfabric.".format(res._id))
        return jsonify({"id": res._id})

    except:
        print(res)
        return jsonify({"error": "beaming dataset to bfabric failed."})


# @deprecated("Use read instead")
@app.route("/user/<int:containerid>", methods=["GET"])
def get_user(containerid):

    users = bfapp.read_object(endpoint="user", obj={"containerid": containerid})
    # not users or
    if not users or len(users) == 0:
        return jsonify({"error": "no resources found."})
        # abort(404)

    return jsonify({"user": users})


# @deprecated("Use read instead")
@app.route("/sample/<int:containerid>", methods=["GET"])
def get_all_sample(containerid):

    samples = []
    rv = list(
        map(
            lambda p: bfapp.read_object(endpoint="sample", obj={"containerid": containerid}, page=p),
            range(1, 10),
        )
    )
    rv = list(map(lambda x: [] if x is None else x, rv))
    for el in rv:
        samples.extend(el)

    try:
        annotationDict = {}
        for annotationId in filter(
            lambda x: x is not None,
            set(map(lambda x: x.groupingvar._id if "groupingvar" in x else None, samples)),
        ):
            print(annotationId)
            annotation = bfapp.read_object(endpoint="annotation", obj={"id": annotationId})
            annotationDict[annotationId] = annotation[0].name
    except:
        pass

    for sample in samples:
        try:
            sample["condition"] = annotationDict[sample.groupingvar._id]
        except:
            sample["condition"] = None

    if len(samples) == 0:
        return jsonify({"error": "no extract found."})
        # abort(404)

    return jsonify({"samples": samples})


"""
example
curl http://localhost:5000/zip_resource_of_workunitid/154547
"""


@app.route("/zip_resource_of_workunitid/<int:workunitid>", methods=["GET"])
def get_zip_resources_of_workunit(workunitid):
    res = map(
        lambda x: x.relativepath,
        bfapp.read_object(endpoint="resource", obj={"workunitid": workunitid}),
    )
    print(res)
    res = filter(lambda x: x.endswith(".zip"), res)
    return jsonify(res)


@app.route("/query", methods=["GET", "POST"])
def query():
    try:
        content = json.loads(request.data)
    except:
        return jsonify({"error": "could not get POST content.", "appid": appid})

    print("PASSWORD CLEARTEXT", content["webservicepassword"])

    bf = bfabric.Bfabric(
        login=content["login"],
        password=content["webservicepassword"],
        base_url="http://fgcz-bfabric.uzh.ch/bfabric",
    )

    for i in content.keys():
        print("{}\t{}".format(i, content[i]))

    if "containerid" in content:
        workunits = bf.read_object(
            endpoint="workunit",
            obj={
                "applicationid": content["applicationid"],
                "containerid": content["containerid"],
            },
        )
        print(workunits)
        return jsonify({"workunits": map(lambda x: x._id, workunits)})
    # elif 'query' in content and "{}".format(content['query']) is 'project':
    else:
        user = bf.read_object(endpoint="user", obj={"login": content["login"]})[0]
        projects = map(lambda x: x._id, user.project)
        return jsonify({"projects": projects})

    return jsonify({"error": "could not process query"})


@app.route("/addworkunit", methods=["GET", "POST"])
def add_workunit():
    appid = request.args.get("appid", None)
    pid = request.args.get("pid", None)
    rname = request.args.get("rname", None)

    try:
        content = json.loads(request.data)
        # print content
    except:
        return jsonify({"error": "could not get POST content.", "appid": appid})

    resource_base64 = content["base64"]
    # base64.b64encode(content)
    print(resource_base64)

    return jsonify({"rv": "ok"})


def main():
    if exists("/etc/ssl/fgcz-host.pem") and exists("/etc/ssl/private/fgcz-host_key.pem"):
        setup_logger_prod()
        app.run(
            debug=False,
            host="0.0.0.0",
            port=5001,
            ssl_context=(
                "/etc/ssl/fgcz-host.pem",
                "/etc/ssl/private/fgcz-host_key.pem",
            ),
        )
    else:
        setup_logger_debug()
        app.run(debug=False, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from dci.analytics import access_data_layer as a_d_l
from dci_analytics import elasticsearch as es
from dci_analytics import dci_db
from dci_analytics import config


from dciclient.v1.api import context
from dciclient.v1.api import file as dci_file

import io

from xml.etree import ElementTree
from xml.parsers.expat import errors as xml_errors
from datetime import timedelta


logger = logging.getLogger(__name__)

_INDEX = "jobs"


def parse_time(string_value):
    try:
        return float(string_value)
    except ValueError:
        return 0.0


def parse_properties(root):
    properties = []
    for child in root:
        tag = child.tag
        if tag != "property":
            continue
        property_name = child.get("name", "").strip()
        property_value = child.get("value", "")
        if property_name:
            properties.append({"name": property_name, "value": property_value})
    return properties


def parse_testcase(testcase_xml):
    testcase = {
        "name": testcase_xml.attrib.get("name", ""),
        "classname": testcase_xml.attrib.get("classname", ""),
        "time": parse_time(testcase_xml.attrib.get("time", "0")),
        "action": "success",
        "message": None,
        "type": None,
        "value": "",
        "stdout": None,
        "stderr": None,
        "properties": [],
    }
    for testcase_child in testcase_xml:
        tag = testcase_child.tag
        if tag not in [
            "skipped",
            "error",
            "failure",
            "system-out",
            "system-err",
        ]:
            continue
        text = testcase_child.text
        if tag == "system-out":
            testcase["stdout"] = text
        elif tag == "system-err":
            testcase["stderr"] = text
        else:
            testcase["action"] = tag
            testcase["message"] = testcase_child.get("message", None)
            testcase["type"] = testcase_child.get("type", None)
            testcase["value"] = text
        testcase_child.clear()
    return testcase


def parse_testsuite(testsuite_xml):
    testsuite = {
        "id": 0,
        "name": testsuite_xml.attrib.get("name", ""),
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "success": 0,
        "time": 0,
        "testcases": [],
        "properties": [],
    }
    testsuite_duration = timedelta(seconds=0)
    for testcase_xml in testsuite_xml:
        tag = testcase_xml.tag
        if tag == "testcase":
            testcase = parse_testcase(testcase_xml)
            testsuite_duration += timedelta(seconds=testcase["time"])
            testsuite["tests"] += 1
            action = testcase["action"]
            if action == "skipped":
                testsuite["skipped"] += 1
            elif action == "error":
                testsuite["errors"] += 1
            elif action == "failure":
                testsuite["failures"] += 1
            else:
                testsuite["success"] += 1
            testsuite["testcases"].append(testcase)
        elif tag == "properties":
            testsuite["properties"] = parse_properties(testcase_xml)
    testsuite["time"] = testsuite_duration.total_seconds()
    return testsuite


def parse_junit(file_descriptor):
    try:
        testsuites = []
        nb_of_testsuites = 0
        for event, element in ElementTree.iterparse(file_descriptor):
            if element.tag == "testsuite":
                testsuite = parse_testsuite(element)
                testsuite["id"] = nb_of_testsuites
                nb_of_testsuites += 1
                testsuites.append(testsuite)
                element.clear()
        return testsuites
    except ElementTree.ParseError as parse_error:
        error_code_no_elements = xml_errors.codes[xml_errors.XML_ERROR_NO_ELEMENTS]
        if parse_error.code == error_code_no_elements:
            return []
        raise parse_error


def get_file_content(api_conn, f):
    r = dci_file.content(api_conn, f["id"])
    return r.content


def get_tests(files, api_conn):
    tests = []
    for f in files:
        if f["state"] != "active":
            continue
        if f["mime"] == "application/junit":
            try:
                file_content = get_file_content(api_conn, f)
                file_descriptor = io.StringIO(file_content.decode("utf-8"))
                tests.append(parse_junit(file_descriptor))
            except Exception as e:
                logger.error(f"Exception during sync: {e}")
    return tests


def process(job, api_conn):
    _id = job["id"]
    doc = es.get(_INDEX, _id)
    job["tests"] = get_tests(job["files"], api_conn)
    if not doc:
        es.push(_INDEX, job, _id)
    else:
        es.update(_INDEX, job, _id)
    return job


def _sync(index, unit, amount):
    es.update_index(
        index,
        json={
            "mappings": {
                "dynamic_templates": [
                    {
                        "strings_as_keyword": {
                            "match_mapping_type": "string",
                            "mapping": {"type": "keyword"},
                        },
                    }
                ],
                "properties": {
                    "comment": {"type": "text"},
                    "components": {"type": "nested"},
                    "team": {"type": "nested"},
                    "topic": {"type": "nested"},
                    "pipeline": {"type": "nested"},
                    "remoteci": {"type": "nested"},
                    "keys_values": {"type": "nested"},
                    "tests": {"type": "nested"},
                },
            }
        },
    )

    _config = config.get_config()
    api_conn = context.build_dci_context(
        dci_login=_config["DCI_LOGIN"],
        dci_password=_config["DCI_PASSWORD"],
        dci_cs_url=_config["DCI_CS_URL"],
    )

    session_db = dci_db.get_session_db()
    limit = 100
    offset = 0

    while True:
        jobs = a_d_l.get_jobs(session_db, offset, limit, unit=unit, amount=amount)
        if not jobs:
            break
        for job in jobs:
            try:
                logger.info("process job %s" % job["id"])
                process(job, api_conn)
            except Exception as e:
                logger.error(
                    "error while processing job '%s': %s" % (job["id"], str(e))
                )
        offset += limit
    session_db.close()


def partial(_lock_synchronization):
    latest_index_alias = es.get_latest_index_alias(_INDEX)
    logger.debug(f"latest index alias: '{latest_index_alias}'")
    _sync(latest_index_alias, "hours", 6)
    _lock_synchronization.release()


def full(_lock_synchronization):
    new_index_name = es.generate_new_index_name(_INDEX)
    logger.debug(f"new index created: '{new_index_name}'")
    _sync(new_index_name, "weeks", 52)
    new_alias = es.add_alias_to_index(new_index_name)
    logger.debug(f"new alias '{new_alias}' added for index: '{new_index_name}'")
    _lock_synchronization.release()

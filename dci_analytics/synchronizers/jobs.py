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

import json
import logging

import concurrent.futures

from dci.analytics import access_data_layer as a_d_l
from dci_analytics import elasticsearch as es
from dci_analytics import dci_db
from dci_analytics import config


from dciclient.v1.api import context

import io

from xml.etree import ElementTree
from xml.parsers.expat import errors as xml_errors
from datetime import timedelta


logger = logging.getLogger(__name__)

_INDEX = "jobs"
_INDEX_JUNIT_CACHE = "jobs_cache_junit"


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
        if tag not in ["skipped", "error", "failure"]:
            continue
        testcase["action"] = tag
        testcase["message"] = testcase_child.get("message", None)
        testcase["type"] = testcase_child.get("type", None)
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


def get_file_content(api_conn, f_id):
    _config = config.CONFIG
    api_url = _config["DCI_CS_URL"]
    r = api_conn.session.get(f"{api_url}/api/v2/files/{f_id}/content")
    return r.content


def get_tests_from_api(files, api_conn):
    tests = []
    for f in files:
        if f["state"] != "active":
            continue
        if f["mime"] == "application/junit":
            test = {"name": f["name"], "file_id": f["id"]}
            try:
                file_content = get_file_content(api_conn, f["id"])
                file_descriptor = io.StringIO(file_content.decode("utf-8"))
                test["testsuites"] = parse_junit(file_descriptor)
                tests.append(test)
            except Exception as e:
                logger.error(f"Exception during sync: {e}")
    return tests


def get_tests_from_cache(job_id):
    doc = es.get(_INDEX_JUNIT_CACHE, job_id)
    if doc:
        return doc["tests"]
    return


def get_tests(job, api_conn):
    tests = get_tests_from_cache(job["id"])
    if tests:
        return tests
    else:
        tests = get_tests_from_api(job["files"], api_conn)
        es.push(
            _INDEX_JUNIT_CACHE,
            {"created_at": job["created_at"], "tests": tests},
            job["id"],
        )
    return tests


def clean_doted_keys(json_content):
    res = {}
    if isinstance(json_content, dict):
        for k, v in json_content.items():
            if "." in k:
                if isinstance(v, dict) or isinstance(v, list):
                    res[k.replace(".", "_")] = clean_doted_keys(v)
                else:
                    res[k.replace(".", "_")] = v
            else:
                res[k] = v
    elif isinstance(json_content, list):
        res = [clean_doted_keys(d) for d in json_content]

    return res


def parse_json(file_content):
    json_content = json.loads(file_content)
    return clean_doted_keys(json_content)


def get_extra_data(job, api_conn):
    extra = []
    for f in job["files"]:
        if f["state"] != "active":
            continue
        if f["mime"] == "application/dci-analytics+json":
            try:
                file_content = get_file_content(api_conn, f["id"])
                file_json = parse_json(file_content)
                extra.append(file_json)
            except Exception as e:
                logger.error(f"Exception during getting extra data: {e}")
    return extra


def process(index, job, api_conn):
    _id = job["id"]
    job["tests"] = get_tests(job, api_conn)
    job["extra"] = get_extra_data(job, api_conn)

    doc = es.get(index, _id)
    if not doc:
        es.push(index, job, _id)
    else:
        es.update(index, job, _id)
    return job


def update_index(index):
    return es.update_index(
        index,
        json={
            "mappings": {
                "dynamic_templates": [
                    {
                        "strings_as_keyword": {
                            "match_mapping_type": "string",
                            "mapping": {"type": "keyword"},
                        }
                    },
                    {
                        "extra_to_nested": {
                            "path_match": "extra.*",
                            "match_mapping_type": "object",
                            "mapping": {"type": "nested"},
                        },
                    },
                ],
                "properties": {
                    "components": {"type": "nested"},
                    "team": {"type": "nested"},
                    "topic": {"type": "nested"},
                    "pipeline": {"type": "nested"},
                    "remoteci": {"type": "nested"},
                    "keys_values": {"type": "nested"},
                    "product": {"type": "nested"},
                    "tests": {
                        "type": "nested",
                        "properties": {
                            "testsuites": {
                                "type": "nested",
                                "properties": {"testcases": {"type": "nested"}},
                            }
                        },
                    },
                    "extra": {"type": "nested"},
                },
            },
            "settings": {
                "index.mapping.nested_objects.limit": 300000,
                "index.mapping.total_fields.limit": 20000,
            },
        },
    )


def _get_api_connection():
    _config = config.CONFIG
    if _config["DCI_CLIENT_ID"] and _config["DCI_API_SECRET"]:
        return context.build_signature_context(
            dci_cs_url=_config["DCI_CS_URL"],
            dci_client_id=_config["DCI_CLIENT_ID"],
            dci_api_secret=_config["DCI_API_SECRET"],
        )
    elif _config["DCI_LOGIN"] and _config["DCI_PASSWORD"]:
        return context.build_dci_context(
            dci_cs_url=_config["DCI_CS_URL"],
            dci_login=_config["DCI_LOGIN"],
            dci_password=_config["DCI_PASSWORD"],
        )
    else:
        logger.error("no credentials found for the api")


def _sync(index, unit, amount):

    is_index_created = update_index(index)
    api_conn = _get_api_connection()

    session_db = dci_db.get_session_db()
    limit = 100
    offset = 0
    last_job = None

    if is_index_created:
        jobs = a_d_l.get_jobs(session_db, 0, 1, unit=unit, amount=amount)
        if len(jobs) > 0:
            es.update_index_meta(index, first_job_date=jobs[0]["created_at"])

    while True:
        jobs = a_d_l.get_jobs(session_db, offset, limit, unit=unit, amount=amount)
        if not jobs:
            break
        last_job = jobs[-1]
        futures = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for job in jobs:
                try:
                    logger.info("process job %s" % job["id"])
                    futures.append(
                        executor.submit(
                            process, index=index, job=job, api_conn=api_conn
                        )
                    )
                except Exception as e:
                    logger.error(
                        "error while processing job '%s': %s" % (job["id"], str(e))
                    )
            for _ in concurrent.futures.as_completed(futures):
                pass
        offset += limit

    if last_job:
        es.update_index_meta(index, last_job_date=last_job["updated_at"])
    session_db.close()


def sync_one_job(index, job):

    is_index_created = update_index(index)
    api_conn = _get_api_connection()

    if is_index_created:
        es.update_index_meta(index, first_job_date=job["created_at"])

    process(index, job, api_conn)

    es.update_index_meta(index, last_job_date=job["updated_at"])


def partial(_lock_synchronization):
    latest_index_alias = es.get_latest_index_alias(_INDEX)
    logger.debug(f"latest index alias: '{latest_index_alias}'")
    _sync(latest_index_alias, "hours", 6)
    _lock_synchronization.release()


def full(_lock_synchronization):
    new_index_name = es.generate_new_index_name(_INDEX)
    logger.debug(f"new index created: '{new_index_name}'")
    _sync(new_index_name, "weeks", 52)
    new_alias = es.add_alias_to_index("jobs", new_index_name)
    logger.debug(f"new alias '{new_alias}' added for index: '{new_index_name}'")
    _lock_synchronization.release()

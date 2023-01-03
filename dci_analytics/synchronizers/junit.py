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

from xml.etree import ElementTree

from dci.analytics import access_data_layer as a_d_l

from dci_analytics import elasticsearch as es
from dci_analytics import dci_db
from dci_analytics import config

from dciclient.v1.api import context
from dciclient.v1.api import file as dci_file

import io
import logging


logger = logging.getLogger()


def junit_to_dict(file_descriptor, filename):
    def _process_testsuite(testsuite, res):
        for tc in testsuite:
            if tc.tag != "testcase":
                continue
            classname = tc.get("classname")
            name = tc.get("name")
            if not classname or not name:
                continue
            key = "%s/%s" % (tc.get("classname"), tc.get("name"))
            key = key.strip()
            key = key.replace(",", "_")
            if tc.get("time"):
                try:
                    res[key] = float(tc.get("time"))
                except Exception:
                    res[key] = -1.0
            else:
                res[key] = -1.0

    res = dict()
    try:
        for _, element in ElementTree.iterparse(file_descriptor):
            if element.tag == "testsuite":
                _process_testsuite(element, res)
    except ElementTree.ParseError as e:
        logger.error("ParseError %s: %s" % (filename, str(e)))
    return res


def get_file_content(api_conn, f):
    r = dci_file.content(api_conn, f["id"])
    return r.content


def _process_sync(api_conn, job):
    files = []
    junit_found = False
    for f in job["files"]:
        if f["state"] != "active":
            continue
        if f["mime"] == "application/junit":
            try:
                junit_found = True
                file_content = get_file_content(api_conn, f)
                file_descriptor = io.StringIO(file_content.decode("utf-8"))
                f["junit_content"] = junit_to_dict(file_descriptor, f["name"])
                files.append(f)
            except Exception as e:
                logger.error(f"Exception during sync: {e}")
    if not junit_found:
        return
    job["files"] = files
    job.pop("jobstates")
    es.push("tasks_junit", job, job["id"])


def _sync(unit, amount):
    es.init_index(
        "tasks_junit",
        json={
            "properties": {
                "topic_id": {"type": "keyword"},
                "remoteci_id": {"type": "keyword"},
                "team_id": {"type": "keyword"},
                "files.junit_content": {"enabled": False},
            }
        },
    )
    session_db = dci_db.get_session_db()
    _config = config.get_config()
    api_conn = context.build_dci_context(
        dci_login=_config["DCI_LOGIN"],
        dci_password=_config["DCI_PASSWORD"],
        dci_cs_url=_config["DCI_CS_URL"],
    )
    limit = 10
    offset = 0
    while True:
        jobs = a_d_l.get_jobs(
            session_db, offset, limit, unit=unit, amount=amount, status="success"
        )
        if not jobs:
            logger.info("no jobs to get from the api")
            break
        logger.info("got %s jobs from the api" % len(jobs))
        for job in jobs:
            logger.info("process job %s" % job["id"])
            row = es.get("tasks_junit", job["id"])
            if row:
                continue
            try:
                _process_sync(api_conn, job)
            except Exception as e:
                logger.error(
                    "error while processing job '%s': %s" % (job["id"], str(e))
                )
        offset += limit

    session_db.close()


def partial(_lock_synchronization):
    _sync("hours", 6)
    _lock_synchronization.release()


def full(_lock_synchronization):
    _sync("weeks", 12)
    _lock_synchronization.release()

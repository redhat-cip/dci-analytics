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


from lxml import etree

from dci.analytics import access_data_layer as a_d_l

from dci_analytics.engine import elasticsearch as es
from dci_analytics.engine import dci_db
from dci_analytics import config

from dciclient.v1.api import context
from dciclient.v1.api import file as dci_file

import logging
import pandas as pd


logger = logging.getLogger()


def junit_to_dict(junit):
    def _process_testcases(testsuite, res):
        for tc in testsuite:
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
        root = etree.fromstring(junit)
        if root.tag == "testsuites":
            for testsuite in root.findall("testsuite"):
                _process_testcases(testsuite, res)
        else:
            _process_testcases(root, res)

    except etree.XMLSyntaxError as e:
        logger.error("XMLSyntaxError %s" % str(e))
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
            junit_found = True
            file_content = get_file_content(api_conn, f)
            f["junit_content"] = junit_to_dict(file_content)
            files.append(f)
    if not junit_found:
        return
    job["files"] = files
    job.pop("jobstates")
    es.push("tasks_junit", job, job["id"])


def _sync(unit, amount):
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
        jobs = a_d_l.get_jobs(session_db, offset, limit, unit=unit, amount=amount)
        if not jobs:
            logger.info("no jobs to get from the api")
            break
        logger.info("got %s jobs from the api" % len(jobs))
        for job in jobs:
            logger.info("process job %s" % job["id"])
            row = es.search("tasks_junit", "q=id:%s" % job["id"])
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


def synchronize(_lock_synchronization):
    _sync("hours", 2)
    _lock_synchronization.release()


def full_synchronize(_lock_synchronization):
    _sync("weeks", 8)
    _lock_synchronization.release()


def filter_jobs(jobs, file_test_name):
    """keep only the job information with the junit content according to the file testname"""
    res = []
    for j in jobs:
        j = j["_source"]
        for f in j["files"]:
            if f["name"] == file_test_name:
                j["junit_content"] = f["junit_content"]
                res.append(
                    {
                        "id": j["id"],
                        "created_at": j["created_at"],
                        "junit_content": f["junit_content"],
                    }
                )
                break
    return res


def get_jobs_dataset(topic_id, start_date, end_date, remoteci_id, test_name):

    jobs_dataframes = []
    jobs_ids_dates = []
    size = 5
    body = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": start_date, "lt": end_date}}},
                    {"term": {"topic_id": topic_id}},
                    {"term": {"remoteci_id": remoteci_id}},
                ]
            }
        },
        "from": 0,
        "size": size,
        "sort": [
            {
                "created_at": {
                    "order": "desc",
                    "format": "strict_date_optional_time_nanos",
                }
            }
        ],
    }
    while True:
        jobs = es.search_json("tasks_junit", body)
        if not jobs:
            break
        jobs = filter_jobs(jobs, test_name)
        for j in jobs:
            df = pd.DataFrame(j["junit_content"], index=[j["id"]])
            jobs_dataframes.append(df)
            jobs_ids_dates.append(
                {
                    "date": j["created_at"],
                    "id": j["id"],
                }
            )
        body["from"] += size

    if not jobs_dataframes:
        return None, None
    return pd.concat(jobs_dataframes), jobs_ids_dates


def topics_comparison(
    topic_name_1,
    topic_1_start_date,
    topic_1_end_date,
    remoteci_1,
    topic_1_baseline_computation,
    topic_name_2,
    topic_2_start_date,
    topic_2_end_date,
    remoteci_2,
    topic_2_baseline_computation,
    test_name,
):
    topic_1_jobs, _ = get_jobs_dataset(
        topic_name_1, topic_1_start_date, topic_1_end_date, remoteci_1, test_name
    )
    if topic_1_baseline_computation == "mean":
        topic_1_jobs_computed = topic_1_jobs.mean()
    elif topic_1_baseline_computation == "median":
        topic_1_jobs_computed = topic_1_jobs.median()
    else:
        # use only the latest job results
        topic_1_jobs_computed = topic_1_jobs.iloc[-1]

    topic_2_jobs, _ = get_jobs_dataset(
        topic_name_2, topic_2_start_date, topic_2_end_date, remoteci_2, test_name
    )
    if topic_2_baseline_computation == "mean":
        topic_2_jobs = topic_2_jobs.mean().to_frame()
    elif topic_2_baseline_computation == "median":
        topic_2_jobs = topic_2_jobs.median().to_frame()
    else:
        # use only the latest job results
        topic_2_jobs = topic_2_jobs.iloc[-1:].T

    def delta(lign):
        if lign.name not in topic_1_jobs.columns.values:
            return "N/A"
        diff = lign - topic_1_jobs_computed[lign.name]
        return (diff * 100.0) / topic_1_jobs_computed[lign.name]

    return topic_2_jobs.apply(delta, axis=1)

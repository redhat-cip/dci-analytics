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


from dci.analytics import access_data_layer as a_d_l
from dci_analytics.engine import elasticsearch as es
from dci_analytics.engine import dci_db

import logging


logger = logging.getLogger(__name__)


def sort_components(headers, components):
    components = sorted(components, key=lambda c: c["canonical_project_name"])
    component_length = len(components)
    res = []
    j = 0
    for i in range(len(headers)):
        h = headers[i]
        if j < component_length:
            if components[j]["canonical_project_name"].startswith(h):
                res.append(components[j])
                j += 1
            else:
                res.append(None)
        else:
            res.append(None)
    return res


def format_tests(job):

    tests = {"success": 0, "failures": 0, "errors": 0, "total": 0, "skips": 0}
    for r in job["results"]:
        tests["success"] += r["success"]
        tests["failures"] += r["failures"]
        tests["errors"] += r["errors"]
        tests["total"] += r["total"]
        tests["skips"] += r["skips"]

    return tests


def _process(job):
    if job["status"] not in {"success", "failure"}:
        return
    if job["pipeline_id"] is None:
        logger.info("not a pipeline job")
        return

    pipeline_id = job["pipeline"]["id"]
    pipeline_name = job["pipeline"]["name"]
    job_name = job["name"]
    doc_id = f"{pipeline_id}-{job_name}"

    doc = es.get("pipelines_status", doc_id)

    logger.info(f"push job {job_name} of pipeline {pipeline_name}")

    if doc:
        es.update("pipelines_status", job, doc_id)
    else:
        es.push("pipelines_status", job, doc_id)


def _sync(unit, amount):

    es.init_index(
        "pipelines_status",
        json={
            "properties": {
                "pipeline.name": {"type": "keyword"},
                "team_id": {"type": "keyword"},
                "components.type": {"type": "keyword"},
            }
        },
    )

    session_db = dci_db.get_session_db()
    limit = 100
    offset = 0

    while True:
        jobs = a_d_l.get_jobs(session_db, offset, limit, unit=unit, amount=amount)
        if not jobs:
            break
        for job in jobs:
            logger.info("process job %s" % job["id"])
            try:
                _process(job)
            except Exception as e:
                logger.error(
                    "error while processing job '%s': %s" % (job["id"], str(e))
                )
        offset += limit

    session_db.close()


def synchronize(_lock_synchronization):
    _sync("hours", 6)
    _lock_synchronization.release()


def full_synchronize(_lock_synchronization):
    _sync("weeks", 24)
    _lock_synchronization.release()

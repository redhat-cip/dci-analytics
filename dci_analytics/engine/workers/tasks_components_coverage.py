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
from dci_analytics.engine import elasticsearch as es
from dci_analytics.engine import dci_db
from dci_analytics import config


logger = logging.getLogger(__name__)

_ES_URL = config.CONFIG.get("ELASTICSEARCH_URL")


def format_component_coverage(component, team_id, job=None):
    res = {
        "id": component["id"],
        "name": component["name"],
        "canonical_project_name": component["canonical_project_name"],
        "product_id": component.get("product_id", ""),
        "topic_id": component["topic_id"],
        "tags": component["tags"],
        "type": component["type"],
        "created_at": component["created_at"],
        "released_at": component["released_at"],
        "team_id": team_id,
        "success_jobs": [],
        "failed_jobs": [],
    }
    if job is not None:
        _job = {"id": job["id"], "created_at": job["created_at"], "name": job["name"]}
        if job["status"] == "success":
            res["success_jobs"] = [_job]
        else:
            res["failed_jobs"] = [_job]
    return res


def update_component_coverage(job, component_coverage):
    data = {}
    _job = {"id": job["id"], "created_at": job["created_at"], "name": job["name"]}
    if job["status"] == "success":
        success_job_ids = {cc["id"] for cc in component_coverage["success_jobs"]}
        if job["id"] not in success_job_ids:
            data["success_jobs"] = component_coverage["success_jobs"] + [_job]
            return True, data
    else:
        failed_job_ids = {cc["id"] for cc in component_coverage["failed_jobs"]}
        if job["id"] not in failed_job_ids:
            data["failed_jobs"] = component_coverage["failed_jobs"] + [_job]
            return True, data
    return False, data


def process(job):
    if "components" not in job:
        return
    components = dict()
    job_components = job["components"]
    for c in job_components:
        c["product_id"] = job["product_id"]
        components[c["id"]] = c
        for team in (job["team_id"], "red_hat"):
            f_c = format_component_coverage(c, team, job)
            row = es.search(
                "tasks_components_coverage",
                "q=id:%s AND team_id:%s AND topic_id:%s"
                % (f_c["id"], team, job["topic_id"]),
            )
            row = row[0] if len(row) > 0 else []
            if not row:
                if team == "red_hat":
                    row_id = "red_hat-%s" % f_c["id"]
                else:
                    row_id = f_c["id"]
                es.push("tasks_components_coverage", f_c, row_id)
            else:
                do_update, data = update_component_coverage(job, row["_source"])
                if do_update:
                    es.update("tasks_components_coverage", data, row["_id"])
    return components


def _sync(unit, amount):
    json = {
        "properties": {
            "topic_id": {"type": "keyword"},
            "team_id": {"type": "keyword"},
            "type": {"type": "keyword"},
        }
    }
    es.init_index("tasks_components_coverage", json=json)
    session_db = dci_db.get_session_db()
    limit = 100
    offset = 0
    all_components = dict()
    components_processed_ids = set()
    components_processed = dict()

    # get all components within the timeframe
    while True:
        components = a_d_l.get_components(
            session_db, offset, limit, unit=unit, amount=amount
        )
        if not components:
            break
        for c in components:
            all_components[c["id"]] = c
        offset += limit

    # process all the jobs within the same timeframe
    offset = 0
    while True:
        jobs = a_d_l.get_jobs(session_db, offset, limit, unit=unit, amount=amount)
        if not jobs:
            break
        for job in jobs:
            logger.info("process job %s" % job["id"])
            try:
                current_components_processed = process(job)
                components_processed.update(current_components_processed)
            except Exception as e:
                logger.error(
                    "error while processing job '%s': %s" % (job["id"], str(e))
                )
        offset += limit

    # if a component is not in the component_processsed_ids set
    # it means it has not been tested yet
    # action: push it on elasticsearch without jobs
    components_processed_ids = set(components_processed.keys())
    for _, v in all_components.items():
        if v["id"] not in components_processed_ids:
            if v["team_id"]:
                f_c = format_component_coverage(v, v["team_id"])
                es.push("tasks_components_coverage", f_c, v["id"])
            else:
                f_c = format_component_coverage(v, "red_hat")
                es.push("tasks_components_coverage", f_c, "red_hat-%s" % v["id"])

    session_db.close()


def synchronize(_lock_synchronization):
    _sync("hours", 6)
    _lock_synchronization.release()


def full_synchronize(_lock_synchronization):
    _sync("weeks", 24)
    _lock_synchronization.release()

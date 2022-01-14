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
import uuid

from dci_analytics.engine import elasticsearch as es


logger = logging.getLogger(__name__)


def format_component_coverage(job, component, team_id):
    res = {
        "component_id": component["id"],
        "component_name": component["name"],
        "product_id": job["product_id"],
        "topic_id": job["topic_id"],
        "tags": component["tags"],
        "team_id": team_id,
        "success_jobs": [],
        "failed_jobs": [],
    }
    if job["status"] == "success":
        res["success_jobs"] = [{"id": job["id"], "created_at": job["created_at"]}]
    else:
        res["failed_jobs"] = [{"id": job["id"], "created_at": job["created_at"]}]
    return res


def update_component_coverage(job, component_coverage):
    data = {}
    if job["status"] == "success":
        success_job_ids = {cc["id"] for cc in component_coverage["success_jobs"]}
        if job["id"] not in success_job_ids:
            data["success_jobs"] = component_coverage["success_jobs"] + [
                {"id": job["id"], "created_at": job["created_at"]}
            ]
            return True, data
    else:
        failed_job_ids = {cc["id"] for cc in component_coverage["failed_jobs"]}
        if job["id"] not in failed_job_ids:
            data["failed_jobs"] = component_coverage["failed_jobs"] + [
                {"id": job["id"], "created_at": job["created_at"]}
            ]
            return True, data
    return False, data


def process(job):
    components = job["components"]
    for c in components:
        for team in (job["team_id"], "red_hat"):
            f_c = format_component_coverage(job, c, team)
            row = es.search(
                "tasks_components_coverage",
                "q=component_id:%s AND team_id:%s" % (f_c["component_id"], team),
            )
            row = row[0] if len(row) > 0 else []
            if not row:
                es.push("tasks_components_coverage", f_c, str(uuid.uuid4()))
            else:
                do_update, data = update_component_coverage(job, row["_source"])
                if do_update:
                    es.update("tasks_components_coverage", data, row["_id"])

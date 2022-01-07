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


from dci_analytics.engine import elasticsearch as es


def format_component_coverage(job, component):
    res = {
        "component_id": component["id"],
        "component_name": component["name"],
        "product_id": job["product_id"],
        "topic_id": job["topic_id"],
        "tags": component["tags"],
        "team_id": job["team_id"],
        "success_jobs": [],
        "failed_jobs": [],
    }
    if job["status"] == "success":
        res["success_jobs"] = [job["id"]]
    else:
        res["failed_jobs"] = [job["id"]]
    return res


def update_component_coverage(job, component_coverage):
    data = {}
    do_update = False
    if job["status"] == "success":
        new_success_jobs = list(set(component_coverage["success_jobs"] + [job["id"]]))
        if len(new_success_jobs) > len(component_coverage["success_jobs"]):
            data["success_jobs"] = new_success_jobs
            do_update = True
    else:
        new_failed_jobs = list(set(component_coverage["failed_jobs"] + [job["id"]]))
        if len(new_failed_jobs) > len(component_coverage["failed_jobs"]):
            data["failed_jobs"] = new_failed_jobs
            do_update = True
    return do_update, data


def process(job):
    components = job["components"]
    for c in components:
        c = format_component_coverage(job, c)
        es_c = es.get("tasks_components_coverage", c["component_id"])
        if es_c is None:
            es.push("tasks_components_coverage", c, c["component_id"])
        else:
            do_update, data = update_component_coverage(job, es_c)
            if do_update:
                es.update("tasks_components_coverage", data, c["component_id"])

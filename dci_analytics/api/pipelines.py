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

import flask

import json
import logging

from dci_analytics.api import api
from dci_analytics import elasticsearch as es


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


def compute_tests_results(job):

    tests = {"success": 0, "failures": 0, "errors": 0, "total": 0, "skips": 0}
    for r in job["results"]:
        tests["success"] += r["success"]
        tests["failures"] += r["failures"]
        tests["errors"] += r["errors"]
        tests["total"] += r["total"]
        tests["skips"] += r["skips"]

    return tests


def filter_components(components, components_types):
    if not components_types:
        return components
    res = []
    for c in components:
        if c["type"] in components_types:
            res.append(c)
    return res


@api.route("/pipelines_status", strict_slashes=False, methods=["POST"])
def pipelines_status():
    start_date = flask.request.json["start_date"]
    end_date = flask.request.json["end_date"]
    pipelines_names = flask.request.json.get("pipelines_names", [])
    teams_ids = flask.request.json.get("teams_ids", [])
    components_types = flask.request.json.get("components_types", [])
    size = 10
    body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "pipeline.created_at": {"gte": start_date, "lte": end_date}
                        }
                    },
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

    if teams_ids:
        team_id_should_query = {"bool": {"should": []}}
        for team_id in teams_ids:
            team_id_should_query["bool"]["should"].append(
                {"term": {"team_id": team_id}}
            )
        body["query"]["bool"]["must"].append(team_id_should_query)

    if pipelines_names:
        pipeline_name_should_query = {"bool": {"should": []}}
        for pipeline_name in pipelines_names:
            pipeline_name_should_query["bool"]["should"].append(
                {"term": {"pipeline.name": pipeline_name}}
            )
        body["query"]["bool"]["must"].append(pipeline_name_should_query)

    jobs = []
    while True:
        _jobs = es.search_json("pipelines_status", body)
        if "hits" not in _jobs:
            break
        if "hits" not in _jobs["hits"]:
            break
        if not _jobs["hits"]["hits"]:
            break
        for j in _jobs["hits"]["hits"]:
            if "files" in j["_source"]:
                j["_source"].pop("files")
            if "jobstates" in j["_source"]:
                j["_source"].pop("jobstates")
            for c in j["_source"]["components"]:
                if "data" in c:
                    c.pop("data")
            jobs.append(j["_source"])
        body["from"] += size

    def _get_components_headers(jobs, components_types):
        headers = []
        for j in jobs:
            for c in j["components"]:
                if components_types and c["type"] not in components_types:
                    continue
                cpn = c["canonical_project_name"]
                if " " in cpn:
                    cpn = c["canonical_project_name"].split(" ")[0]
                elif ":" in cpn:
                    cpn = c["canonical_project_name"].split(":")[0]
                if cpn not in headers:
                    headers.append(cpn)
        return sorted(headers)

    components_headers = _get_components_headers(jobs, components_types)
    pipelines = {}
    for job in jobs:
        if job["pipeline"]["id"] not in pipelines:
            pipelines[job["pipeline"]["id"]] = {
                "jobs": [],
                "created_at": job["pipeline"]["created_at"].split("T")[0],
                "name": job["pipeline"]["name"],
            }

        job["components"] = filter_components(job["components"], components_types)
        job["components"] = sort_components(components_headers, job["components"])
        job["tests"] = compute_tests_results(job)
        job.pop("results")

        pipelines[job["pipeline"]["id"]]["jobs"].append(job)

    days = {}
    for _, p in pipelines.items():
        if p["created_at"] not in days:
            days[p["created_at"]] = {"date": p["created_at"], "pipelines": [p]}
        else:
            days[p["created_at"]]["pipelines"].append(p)

    return flask.Response(
        json.dumps(
            {"components_headers": components_headers, "days": list(days.values())}
        ),
        status=200,
        content_type="application/json",
    )

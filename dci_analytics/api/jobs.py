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


@api.route("/jobs", strict_slashes=False, methods=["GET"])
def get_jobs():
    latest_index_alias = es.get_latest_index_alias("jobs")
    if not latest_index_alias:
        return flask.Response(
            json.dumps({"message": "no alias for prefix index 'jobs' found"}),
            status=400,
            content_type="application/json",
        )
    values = flask.request.json
    _jobs = es.search_json(latest_index_alias, values)

    if "hits" not in _jobs:
        _jobs = {}
    elif "hits" not in _jobs["hits"]:
        _jobs = {}
    elif not _jobs["hits"]["hits"]:
        _jobs = {}

    _jobs["_meta"] = es.get_index_meta(latest_index_alias)
    return flask.Response(
        json.dumps(_jobs),
        status=200,
        content_type="application/json",
    )


@api.route("/jobs/autocomplete", strict_slashes=False, methods=["GET"])
def get_jobs_autocompletion():
    latest_index_alias = es.get_latest_index_alias("jobs")
    if not latest_index_alias:
        return flask.Response(
            json.dumps({"message": "no alias for prefix index 'jobs' found"}),
            status=400,
            content_type="application/json",
        )
    values = flask.request.json
    if "field" not in values and "team_id" not in values:
        return flask.Response(
            json.dumps({"message": "'field' or 'team_id' parameters missing."}),
            status=400,
            content_type="application/json",
        )
    field = values["field"]
    team_id = values["team_id"]
    is_admin = values.get("is_admin", False)
    size = values.get("size", 10)

    autocompletion_values = es.get_autocompletion_values(
        latest_index_alias, team_id, field, is_admin, size
    )

    return flask.Response(
        json.dumps(autocompletion_values),
        status=200,
        content_type="application/json",
    )

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
    args = flask.request.args.to_dict()
    values = flask.request.json
    q = values["query"]["query_string"]["query"]
    team_id = args["team_id"]
    values["query"]["query_string"]["query"] = "team_id:%s AND (%s)" % (team_id, q)
    values["_source"] = {"exclude": ["jobstates"]}
    _jobs = es.search_json("jobs", values)

    if "hits" not in _jobs:
        _jobs = []
    elif "hits" not in _jobs["hits"]:
        _jobs = []
    elif not _jobs["hits"]["hits"]:
        _jobs = []

    return flask.Response(
        json.dumps(_jobs),
        status=200,
        content_type="application/json",
    )

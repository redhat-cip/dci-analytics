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
import sys
import threading

from dci_analytics.engine.workers import tasks_duration_cumulated
from dci_analytics.engine.workers import tasks_components_coverage


app = flask.Flask(__name__)


logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(levelname)s - %(message)s")
streamhandler = logging.StreamHandler(stream=sys.stdout)
streamhandler.setFormatter(formatter)
logger.addHandler(streamhandler)
logger.setLevel(logging.DEBUG)


_LOCK_TASK_DURATION_CUMULATED = threading.Lock()
_LOCK_TASK_COMPONENTS_COVERAGE = threading.Lock()


@app.route("/ok", strict_slashes=False)
def index():
    return flask.Response(
        json.dumps(
            {
                "_status": "OK",
                "message": "Distributed CI Analytics",
            }
        ),
        status=200,
        content_type="application/json",
    )


def lock_and_run(lock, func):
    if lock.acquire(blocking=False):
        threading.Thread(
            target=func,
            daemon=True,
            args=(lock,),
        ).start()
        return flask.Response(
            json.dumps(
                {
                    "message": "Run synchronization",
                }
            ),
            status=201,
            content_type="application/json",
        )
    else:
        return flask.Response(
            json.dumps(
                {
                    "message": "Already synchronizing, please try later",
                }
            ),
            status=400,
            content_type="application/json",
        )


@app.route("/tasks_duration_cumulated/sync", strict_slashes=False, methods=["POST"])
def tasks_duration_cumulated_sync():
    return lock_and_run(
        _LOCK_TASK_DURATION_CUMULATED, tasks_duration_cumulated.synchronize
    )


@app.route(
    "/tasks_duration_cumulated/full_sync", strict_slashes=False, methods=["POST"]
)
def tasks_duration_cumulated_full_sync():
    return lock_and_run(
        _LOCK_TASK_DURATION_CUMULATED, tasks_duration_cumulated.full_synchronize
    )


@app.route("/tasks_components_coverage/sync", strict_slashes=False, methods=["POST"])
def tasks_components_coverage_sync():
    return lock_and_run(
        _LOCK_TASK_COMPONENTS_COVERAGE, tasks_components_coverage.synchronize
    )


@app.route(
    "/tasks_components_coverage/full_sync", strict_slashes=False, methods=["POST"]
)
def tasks_components_coverage_full_sync():
    return lock_and_run(
        _LOCK_TASK_COMPONENTS_COVERAGE, tasks_components_coverage.full_synchronize
    )

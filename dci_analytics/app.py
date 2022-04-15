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
import threading

from dci_analytics.engine.workers import tasks_duration_cumulated
from dci_analytics.engine.workers import tasks_components_coverage
from dci_analytics.engine.workers import tasks_junit


app = flask.Flask(__name__)


logger = logging.getLogger()
formatter = logging.Formatter("%(levelname)s - %(message)s")
streamhandler = logging.StreamHandler()
streamhandler.setFormatter(formatter)
logger.addHandler(streamhandler)
logger.setLevel(logging.DEBUG)


_LOCK_TASK_DURATION_CUMULATED = threading.Lock()
_LOCK_TASK_COMPONENTS_COVERAGE = threading.Lock()
_LOCK_TASK_JUNIT = threading.Lock()


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


@app.route("/tasks_junit/sync", strict_slashes=False, methods=["POST"])
def tasks_junit_sync():
    return lock_and_run(_LOCK_TASK_JUNIT, tasks_junit.synchronize)


@app.route("/tasks_junit/full_sync", strict_slashes=False, methods=["POST"])
def tasks_junit_full_sync():
    logger.info("running full synchronization")
    return lock_and_run(_LOCK_TASK_JUNIT, tasks_junit.full_synchronize)


@app.route("/junit_topics_comparison", strict_slashes=False, methods=["POST"])
def junit_topics_comparison():
    team_1_id = flask.request.json["team_1_id"]
    topic_1_id = flask.request.json["topic_1_id"]
    topic_1_start_date = flask.request.json["topic_1_start_date"]
    topic_1_end_date = flask.request.json["topic_1_end_date"]
    remoteci_1_id = flask.request.json["remoteci_1"]
    topic_1_baseline_computation = flask.request.json["topic_1_baseline_computation"]
    tags_1 = flask.request.json["tags_1"]

    team_2_id = flask.request.json["team_2_id"]
    topic_2_id = flask.request.json["topic_2_id"]
    topic_2_start_date = flask.request.json["topic_2_start_date"]
    topic_2_end_date = flask.request.json["topic_2_end_date"]
    test_name = flask.request.json["test_name"]
    remoteci_2_id = flask.request.json["remoteci_2"]
    topic_2_baseline_computation = flask.request.json["topic_2_baseline_computation"]
    tags_2 = flask.request.json["tags_2"]

    comparison = tasks_junit.topics_comparison(
        team_1_id,
        topic_1_id,
        topic_1_start_date,
        topic_1_end_date,
        remoteci_1_id,
        topic_1_baseline_computation,
        tags_1,
        team_2_id,
        topic_2_id,
        topic_2_start_date,
        topic_2_end_date,
        remoteci_2_id,
        topic_2_baseline_computation,
        tags_2,
        test_name,
    )

    # Bar chart, histogram
    min = comparison.min() - 1.0
    if isinstance(min, float):
        min = int(min)
    else:
        min = int(min.min())

    max = comparison.max() + 1.0
    if isinstance(max, float):
        max = int(max)
    else:
        max = int(max.max())

    interval = int((max - min) / 25.0)
    if interval == 0:
        interval = 1
    intervals = []
    for i in range(min, max, interval):
        intervals.append((i, i + interval))
    intervals.sort()
    result = {}
    for i in intervals:
        result[i] = 0
    for i in range(0, comparison.shape[0]):
        for j in range(0, comparison.shape[1]):
            value = comparison.iloc[i, j]
            for inter in intervals:
                if value >= inter[0] and value < inter[1]:
                    result[inter] += 1
    values = []
    for inter in intervals:
        values.append(result[inter])

    job_id = comparison.columns.tolist()[0]
    comparison.sort_values(by=job_id, ascending=False, inplace=True)
    testcases = comparison.index.tolist()
    details = []
    for testcase in testcases:
        details.append(
            {"testcase": testcase, "value": comparison.loc[testcase, job_id]}
        )

    return flask.Response(
        json.dumps(
            {
                "values": values,
                "intervals": [[i, j] for i, j in intervals],
                "details": details,
            }
        ),
        status=201,
        content_type="application/json",
    )

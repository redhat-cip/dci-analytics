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

from datetime import datetime as dt
import json
import logging

from dci_analytics import elasticsearch as es
from dci_analytics.api import api
from dci_analytics import exceptions

import flask
import pandas as pd


logger = logging.getLogger()


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


def get_jobs_dataset(topic_id, start_date, end_date, remoteci_id, tags, test_name):

    jobs_dataframes = []
    size = 5
    body = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": start_date, "lte": end_date}}},
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
    if tags:
        for t in tags:
            body["query"]["bool"]["must"].append({"term": {"tags": t}})

    while True:
        jobs = es.search_json("tasks_junit", body)
        if "hits" not in jobs:
            break
        if "hits" not in jobs["hits"]:
            break
        if not jobs:
            break
        jobs = jobs["hits"]["hits"]
        jobs = filter_jobs(jobs, test_name)
        for j in jobs:
            if j["junit_content"]:
                df = pd.DataFrame(j["junit_content"], index=[j["id"]])
                jobs_dataframes.append(df)
        body["from"] += size

    if not jobs_dataframes:
        return None, None
    return pd.concat(jobs_dataframes), len(jobs_dataframes)


def generate_bar_chart_data(tests):
    index = [v for v in range(-100, 101, 10)]
    res = [0] * 20
    for _, v in tests.items():
        for i, vi in enumerate(index):
            if v < -100:
                res[0] += 1
                break
            elif v > 100:
                res[19] += 1
                break
            elif v <= vi:
                res[i - 1] += 1
                break
    return res


def topics_comparison(
    topic_1_id,
    topic_1_start_date,
    topic_1_end_date,
    remoteci_1_id,
    topic_1_baseline_computation,
    tags_1,
    topic_2_id,
    topic_2_start_date,
    topic_2_end_date,
    remoteci_2_id,
    topic_2_baseline_computation,
    tags_2,
    test_name,
):
    topic_1_jobs, len_jobs_topic_1 = get_jobs_dataset(
        topic_1_id,
        topic_1_start_date,
        topic_1_end_date,
        remoteci_1_id,
        tags_1,
        test_name,
    )
    if topic_1_jobs is None:
        raise exceptions.DCIException(
            (
                "no jobs for: topic_id {topic_id}, "
                + "topic_start_date {topic_start_date}, "
                + "topic_end_date {topic_end_date}, "
                + "remoteci_id {remoteci_id}, "
                + "test {test_name}"
            ).format(
                topic_id=topic_1_id,
                topic_start_date=topic_1_start_date,
                topic_end_date=topic_1_end_date,
                remoteci_id=remoteci_1_id,
                test_name=test_name,
            )
        )
    if topic_1_baseline_computation == "mean":
        topic_1_jobs_computed = topic_1_jobs.mean()
    elif topic_1_baseline_computation == "median":
        topic_1_jobs_computed = topic_1_jobs.median()
    else:
        # use only the latest job results
        topic_1_jobs_computed = topic_1_jobs.iloc[-1].T
    topic_1_jobs_computed = topic_1_jobs_computed.dropna()

    topic_2_jobs, len_jobs_topic_2 = get_jobs_dataset(
        topic_2_id,
        topic_2_start_date,
        topic_2_end_date,
        remoteci_2_id,
        tags_2,
        test_name,
    )
    if topic_2_jobs is None:
        raise exceptions.DCIException(
            (
                "no jobs for: topic_id {topic_id}, "
                + "topic_start_date {topic_start_date}, "
                + "topic_end_date {topic_end_date}, "
                + "remoteci_id {remoteci_id}, "
                + "test {test_name}"
            ).format(
                topic_id=topic_2_id,
                topic_start_date=topic_2_start_date,
                topic_end_date=topic_2_end_date,
                remoteci_id=remoteci_2_id,
                test_name=test_name,
            )
        )
    if topic_2_baseline_computation == "mean":
        topic_2_jobs_computed = topic_2_jobs.mean()
    elif topic_2_baseline_computation == "median":
        topic_2_jobs_computed = topic_2_jobs.median()
    else:
        # use only the latest job results
        topic_2_jobs_computed = topic_2_jobs.iloc[-1:].T
    topic_2_jobs_computed = topic_2_jobs_computed.dropna()

    diff = topic_2_jobs_computed - topic_1_jobs_computed
    return (
        ((diff * 100) / topic_1_jobs_computed).dropna(),
        len_jobs_topic_1,
        len_jobs_topic_2,
    )


def check_dates(
    topic_1_start_date, topic_1_end_date, topic_2_start_date, topic_2_end_date
):
    date_topic_1_start_date = dt.strptime(topic_1_start_date, "%Y-%m-%d")
    date_topic_1_end_date = dt.strptime(topic_1_end_date, "%Y-%m-%d")
    if date_topic_1_start_date > date_topic_1_end_date:
        raise exceptions.DCIException(
            "topic_1_end_date is anterior to topic_1_start_date"
        )

    date_topic_2_start_date = dt.strptime(topic_2_start_date, "%Y-%m-%d")
    date_topic_2_end_date = dt.strptime(topic_2_end_date, "%Y-%m-%d")
    if date_topic_2_start_date > date_topic_2_end_date:
        raise exceptions.DCIException(
            "topic_2_end_date is anterior to topic_2_start_date"
        )


@api.route("/junit_topics_comparison", strict_slashes=False, methods=["POST"])
def junit_topics_comparison():
    topic_1_id = flask.request.json["topic_1_id"]
    topic_1_start_date = flask.request.json["topic_1_start_date"]
    topic_1_end_date = flask.request.json["topic_1_end_date"]
    remoteci_1_id = flask.request.json["remoteci_1_id"]
    topic_1_baseline_computation = flask.request.json["topic_1_baseline_computation"]
    tags_1 = flask.request.json["tags_1"]

    topic_2_id = flask.request.json["topic_2_id"]
    topic_2_start_date = flask.request.json["topic_2_start_date"]
    topic_2_end_date = flask.request.json["topic_2_end_date"]
    test_name = flask.request.json["test_name"]
    remoteci_2_id = flask.request.json["remoteci_2_id"]
    topic_2_baseline_computation = flask.request.json["topic_2_baseline_computation"]
    tags_2 = flask.request.json["tags_2"]

    check_dates(
        topic_1_start_date, topic_1_end_date, topic_2_start_date, topic_2_end_date
    )

    comparison, len_jobs_topic_1, len_jobs_topic_2 = topics_comparison(
        topic_1_id,
        topic_1_start_date,
        topic_1_end_date,
        remoteci_1_id,
        topic_1_baseline_computation,
        tags_1,
        topic_2_id,
        topic_2_start_date,
        topic_2_end_date,
        remoteci_2_id,
        topic_2_baseline_computation,
        tags_2,
        test_name,
    )

    # Bar chart, histogram
    comparison.sort_values(ascending=False, inplace=True)
    values = generate_bar_chart_data(comparison)

    comparison_jsonable = []
    for k, v in comparison.items():
        comparison_jsonable.append({"testcase": k, "value": v})

    return flask.Response(
        json.dumps(
            {
                "values": list(values),
                "intervals": [v for v in range(-100, 101, 10)],
                "details": comparison_jsonable,
                "len_jobs_topic_1": len_jobs_topic_1,
                "len_jobs_topic_2": len_jobs_topic_2,
            }
        ),
        status=200,
        content_type="application/json",
    )

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
            _f_name = f["name"].strip().lower()
            _f_test_name = file_test_name.strip().lower()

            is_matching = False
            if _f_test_name.endswith("*"):
                _f_test_name = _f_test_name[:-1]
                is_matching = _f_name.startswith(_f_test_name)
            else:
                is_matching = _f_name == _f_test_name
            if is_matching:
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
                    "order": "asc",
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
        if not jobs["hits"]:
            break
        if "hits" not in jobs["hits"]:
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
    intervals = [v for v in range(-110, 110, 10)]
    res = [0] * len(intervals)
    for _, v in tests.items():
        for i, vi in enumerate(intervals):
            if v < intervals[1]:
                res[0] += 1
                break
            elif v > intervals[len(intervals) - 1]:
                res[len(intervals) - 1] += 1
                break
            elif v < vi:
                res[i - 1] += 1
                break
    return intervals, res


def comparison_data(
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

    # replace 0 values by 1 to avoid zero division
    topic_1_jobs_computed.replace(0, 1, inplace=True)

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

    return (
        topic_1_jobs,
        len_jobs_topic_1,
        topic_2_jobs,
        len_jobs_topic_2,
        topic_1_jobs_computed,
        topic_2_jobs_computed,
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

    (
        _,
        len_jobs_topic_1,
        topic_2_jobs,
        len_jobs_topic_2,
        topic_1_jobs_computed,
        topic_2_jobs_computed,
    ) = comparison_data(
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
    diff = topic_2_jobs_computed - topic_1_jobs_computed
    comparison = ((diff * 100) / topic_1_jobs_computed).dropna()
    comparison.sort_values(ascending=False, inplace=True)
    intervals, values = generate_bar_chart_data(comparison)
    comparison_jsonable = []
    for k, v in comparison.items():
        comparison_jsonable.append({"testcase": k, "value": v})
    bar_chart = {
        "values": list(values),
        "intervals": intervals,
        "details": comparison_jsonable,
        "len_jobs_topic_1": len_jobs_topic_1,
        "len_jobs_topic_2": len_jobs_topic_2,
    }

    # Trend percentage graph
    evolution_percentage_value = 95
    diff = topic_2_jobs - topic_1_jobs_computed
    comparison = ((diff * 100) / topic_1_jobs_computed).dropna()
    float_evolution_percentage_value = float(evolution_percentage_value) / 100.0
    trend_values = []
    for i in range(comparison.shape[0]):
        job_column = []
        for j in range(comparison.shape[1]):
            value = comparison.iloc[i, j]
            job_column.append(value)
        job_column.sort()
        index_percentage = int(len(job_column) * float_evolution_percentage_value)
        if index_percentage >= len(job_column):
            index_percentage = len(job_column) - 1
        trend_values.append(job_column[index_percentage])
    trend_percentage = {"job_ids": comparison.index.tolist(), "values": trend_values}

    return flask.Response(
        json.dumps(
            {
                "bar_chart": bar_chart,
                "trend_percentage": trend_percentage,
                "values": list(values),
                "intervals": intervals,
                "details": comparison_jsonable,
                "len_jobs_topic_1": len_jobs_topic_1,
                "len_jobs_topic_2": len_jobs_topic_2,
            }
        ),
        status=200,
        content_type="application/json",
    )

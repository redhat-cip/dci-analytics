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
from dci_analytics.engine import elasticsearch as es


def get_sorted_tasks(job):
    job_files = []
    for js in job["jobstates"]:
        js["files"] = sorted(
            js["files"],
            key=lambda k: dt.strptime(k["created_at"], "%Y-%m-%dT%H:%M:%S.%f"),
        )
        job_files.extend(js["files"])
    return job_files


def get_task_timestamp(task):
    return dt.strptime(task["created_at"], "%Y-%m-%dT%H:%M:%S.%f")


def get_tasks_duration_cumulated(tasks):
    tasks_duration_cumulated = []
    if not tasks:
        return tasks_duration_cumulated

    if len(tasks) < 2:
        return [{"name": tasks[0]["name"], "duration": 0}]

    # compute absolute duration of each task
    for i in range(len(tasks) - 1):
        timestamp_1 = get_task_timestamp(tasks[i])
        timestamp_2 = get_task_timestamp(tasks[i + 1])
        duration = timestamp_2 - timestamp_1
        tasks_duration_cumulated.append(
            {"name": tasks[i]["name"], "duration": duration.seconds}
        )
    # compute cumulated duration
    for i in range(1, len(tasks_duration_cumulated)):
        tasks_duration_cumulated[i]["duration"] += tasks_duration_cumulated[i - 1][
            "duration"
        ]
    return tasks_duration_cumulated


def format_data(job, tasks_duration_cumulated):
    return {
        "job_id": job["id"],
        "job_name": job["name"],
        "created_at": job["created_at"],
        "topic_id": job["topic_id"],
        "remoteci_id": job["remoteci_id"],
        "data": tasks_duration_cumulated,
    }


def process(job):
    tasks = get_sorted_tasks(job)
    tasks_duration_cumulated = get_tasks_duration_cumulated(tasks)
    data = format_data(job, tasks_duration_cumulated)
    es.push("tasks_duration_cumulated", data, data["job_id"])

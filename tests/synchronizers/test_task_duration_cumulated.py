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

from dci_analytics.synchronizers import duration_cumulated


def test__get_tasks_duration_cumulated():
    tasks = [
        {"created_at": "2021-09-28T20:10:32.162724", "name": "task 1"},
        {"created_at": "2021-09-28T20:12:32.162724", "name": "task 2"},
        {"created_at": "2021-09-28T20:16:32.162724", "name": "task 3"},
        {"created_at": "2021-09-28T20:20:32.162724", "name": "task 4"},
    ]

    expected_duration = {"task 1": 120, "task 2": 360, "task 3": 600}

    _tasks_duration_cumulated = duration_cumulated._get_tasks_duration_cumulated(tasks)
    for tdc in _tasks_duration_cumulated:
        assert expected_duration[tdc["name"]] == tdc["duration"]

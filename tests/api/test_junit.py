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


from dci_analytics import exceptions
from dci_analytics.api import junit


import pytest


def test_generate_bar_chart_data():
    tests = {
        "test_1": -200,
        "test_2": -105,
        "test_3": -75,
        "test_a": -53.28,
        "test_b": -42,
        "test_c": -41,
        "test_d": -40.09,
        "test_4": 5,
        "test_5": 55,
        "test_6": 77,
        "test_7": 120,
    }

    res = junit.generate_bar_chart_data(tests)
    assert res[0] == 2
    assert res[2] == 0
    assert res[5] == 1
    assert res[6] == 3
    assert res[10] == 0
    assert res[11] == 1
    assert res[15] == 0
    assert res[16] == 1
    assert res[17] == 0
    assert res[18] == 1
    assert res[19] == 1


def test_dates():
    topic_1_start_date = "2022-12-01"
    topic_1_end_date = "2022-12-10"
    topic_2_start_date = "2022-12-01"
    topic_2_end_date = "2022-12-10"

    junit.check_dates(
        topic_1_start_date, topic_1_end_date, topic_2_start_date, topic_2_end_date
    )

    topic_1_start_date, topic_1_end_date = topic_1_end_date, topic_1_start_date
    with pytest.raises(exceptions.DCIException):
        junit.check_dates(
            topic_1_start_date, topic_1_end_date, topic_2_start_date, topic_2_end_date
        )


def test_filter_jobs():
    jobs = [
        {
            "_source": {
                "files": [
                    {
                        "name": "TeSt_1",
                        "junit_content": "",
                    }
                ],
                "id": "1",
                "created_at": "",
            }
        },
        {
            "_source": {
                "files": [
                    {
                        "name": "TeSt_2",
                        "junit_content": "",
                    }
                ],
                "id": "2",
                "created_at": "",
            }
        },
    ]

    r = junit.filter_jobs(jobs, "TeSt_1")
    assert len(r) == 1
    assert r[0]["id"] == "1"

    r = junit.filter_jobs(jobs, "Test_1")
    assert len(r) == 1
    assert r[0]["id"] == "1"

    r = junit.filter_jobs(jobs, "test_1")
    assert len(r) == 1
    assert r[0]["id"] == "1"

    r = junit.filter_jobs(jobs, "Test*")
    assert len(r) == 2

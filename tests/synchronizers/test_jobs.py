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

import mock

from dci_analytics.synchronizers import jobs


@mock.patch("dci_analytics.synchronizers.jobs.get_tests_from_cache")
@mock.patch("dci_analytics.synchronizers.jobs.get_tests_from_api")
@mock.patch("dci_analytics.synchronizers.jobs.es.push")
def test_get_tests(m_es_push, m_gtfa, m_gtfc):
    m_gtfc.return_value = []
    m_gtfa.return_value = ["tests"]
    job = {"id": "id", "created_at": "created_at", "files": []}
    tests = jobs.get_tests(job=job, api_conn={})
    m_es_push.assert_called_once_with(
        jobs._INDEX_JUNIT_CACHE, {"created_at": "created_at", "tests": ["tests"]}, "id"
    )
    assert tests == ["tests"]


def test_clean_doted_keys():
    t1 = {"a": "b"}
    assert jobs.clean_doted_keys(t1) == {"a": "b"}

    t2 = {"a.b": "c", "d.f": [{"c.v": "d"}, {"m.d": "ok"}]}
    assert jobs.clean_doted_keys(t2) == {
        "a_b": "c",
        "d_f": [{"c_v": "d"}, {"m_d": "ok"}],
    }

    t3 = {"a.b": "c", "d.f": [{"c.v": [{"lol.lol": "mdr.mdr"}]}, {"m.d": "ok"}]}
    assert jobs.clean_doted_keys(t3) == {
        "a_b": "c",
        "d_f": [{"c_v": [{"lol_lol": "mdr.mdr"}]}, {"m_d": "ok"}],
    }

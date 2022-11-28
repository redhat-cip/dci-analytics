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


from dci_analytics.engine.workers import tasks_junit


def test_generate_bar_chart_data():
    tests = {
        "test_1": -200,
        "test_2": -96,
        "test_3": -80,
        "test_4": 5,
        "test_5": 50,
        "test_6": 70,
        "test_7": 120,
    }

    res = tasks_junit.generate_bar_chart_data(tests)
    assert res[16] == 1
    assert res[19] == 1
    assert res[1] == 1
    assert res[9] == 1
    assert res[14] == 1
    assert res[0] == 2

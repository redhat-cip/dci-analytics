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

from dci_analytics.api import pipelines


def test_sort_components():
    headers = ["a", "c", "d"]
    components = [
        {"display_name": "d abcde"},
        {"display_name": "c fghij"},
        {"display_name": "a klmno"},
    ]
    sorted_components = pipelines.sort_components(headers, components)
    assert sorted_components[0]["display_name"] == "a klmno"
    assert sorted_components[1]["display_name"] == "c fghij"
    assert sorted_components[2]["display_name"] == "d abcde"

    headers = ["a", "b", "c", "d"]
    sorted_components = pipelines.sort_components(headers, components)
    assert sorted_components[0]["display_name"] == "a klmno"
    assert sorted_components[1] is None
    assert sorted_components[2]["display_name"] == "c fghij"
    assert sorted_components[3]["display_name"] == "d abcde"

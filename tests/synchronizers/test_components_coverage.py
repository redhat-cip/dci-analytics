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

from dci_analytics.synchronizers import components_coverage


def test_update_component_coverage():
    job = {
        "status": "success",
        "id": "31d1fb0c-c0e0-4b8d-938e-25e0b0a2682e",
        "created_at": "2022-01-14T00:40:17.145315",
        "name": "job_name",
    }
    c_c = {"success_jobs": [], "failed_jobs": []}
    do_update, data = components_coverage.update_component_coverage(job, c_c)
    assert do_update == True  # noqa
    assert {j["id"] for j in data["success_jobs"]} == {
        "31d1fb0c-c0e0-4b8d-938e-25e0b0a2682e"
    }

    job = {
        "status": "failure",
        "id": "31d1fb0c-c0e0-4b8d-938e-25e0b0a2682e",
        "created_at": "2022-01-15T00:40:17.145315",
        "name": "job_name",
    }
    c_c = {
        "success_jobs": [],
        "failed_jobs": [
            {
                "id": "41d1fb0c-c0e0-4b8d-938e-25e0b0a2682f",
                "created_at": "2022-01-15T00:40:17.145315",
            }
        ],
    }
    do_update, data = components_coverage.update_component_coverage(job, c_c)
    assert do_update == True  # noqa
    assert {j["id"] for j in data["failed_jobs"]} == {
        "31d1fb0c-c0e0-4b8d-938e-25e0b0a2682e",
        "41d1fb0c-c0e0-4b8d-938e-25e0b0a2682f",
    }

    job = {
        "status": "success",
        "id": "31d1fb0c-c0e0-4b8d-938e-25e0b0a2682e",
        "created_at": "2022-01-15T00:40:17.145315",
        "name": "job_name",
    }
    c_c = {
        "success_jobs": [
            {
                "id": "31d1fb0c-c0e0-4b8d-938e-25e0b0a2682e",
                "created_at": "2022-01-15T00:40:17.145315",
            }
        ],
        "failed_jobs": [],
    }
    do_update, data = components_coverage.update_component_coverage(job, c_c)
    assert do_update == False  # noqa
    assert data == {}

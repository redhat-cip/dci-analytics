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

import importlib
import json
import logging
import threading

from dci_analytics.api import api
from dci_analytics import exceptions

logger = logging.getLogger(__name__)

_LOCK_DURATION_CUMULATED = threading.Lock()
_LOCK_COMPONENTS_COVERAGE = threading.Lock()
_LOCK_JUNIT = threading.Lock()
_LOCK_PIPELINES = threading.Lock()
_LOCK_JOBS = threading.Lock()

_LOCKS = {
    "duration_cumulated": _LOCK_DURATION_CUMULATED,
    "components_coverage": _LOCK_COMPONENTS_COVERAGE,
    "junit": _LOCK_JUNIT,
    "pipelines": _LOCK_PIPELINES,
    "jobs": _LOCK_JOBS,
}

_VALID_SYNCHRONIZATION_TYPE = {"partial", "full"}


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


def _run_synchronization(name, synchronization_type):
    if (
        not synchronization_type
        or synchronization_type not in _VALID_SYNCHRONIZATION_TYPE
    ):
        msg = f"{name}: missing or invalid type parameters {synchronization_type}"
        logger.error(msg)
        raise exceptions.DCIException(msg)
    else:
        synchronizer = importlib.import_module(
            name=f".{name}", package="dci_analytics.synchronizers"
        )
        synchronization_function = getattr(synchronizer, synchronization_type)
        logger.info(f"{name}: running {synchronization_type} synchronization")
        return lock_and_run(_LOCKS[name], synchronization_function)


def _get_request_json_key(key, default=None):
    if not flask.request.json:
        return default
    else:
        return flask.request.json.get(key, default)


@api.route(
    "/synchronization/duration_cumulated", strict_slashes=False, methods=["POST"]
)
def duration_cumulated_sync():
    synchronization_type = _get_request_json_key("type", "partial")
    return _run_synchronization("duration_cumulated", synchronization_type)


@api.route(
    "/synchronization/components_coverage", strict_slashes=False, methods=["POST"]
)
def components_coverage_sync():
    synchronization_type = _get_request_json_key("type", "partial")
    return _run_synchronization("components_coverage", synchronization_type)


@api.route("/synchronization/junit", strict_slashes=False, methods=["POST"])
def junit_sync():
    synchronization_type = _get_request_json_key("type", "partial")
    return _run_synchronization("junit", synchronization_type)


@api.route("/synchronization/pipelines", strict_slashes=False, methods=["POST"])
def telco_sync():
    synchronization_type = _get_request_json_key("type", "partial")
    return _run_synchronization("pipelines", synchronization_type)


@api.route("/synchronization/jobs", strict_slashes=False, methods=["POST"])
def jobs_sync():
    synchronization_type = _get_request_json_key("type", "partial")
    return _run_synchronization("jobs", synchronization_type)

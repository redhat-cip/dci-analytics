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

import json
import threading

from dci_analytics.engine import synchronization

app = flask.Flask(__name__)


_LOCK_SYNCHRONIZATION = threading.Lock()


@app.route("/", strict_slashes=False)
def index():
    return flask.Response(
        json.dumps(
            {
                "_status": "OK",
                "message": "Distributed CI Analytics",
            }
        ),
        status=200,
        content_type="application/json",
    )


@app.route("/sync", strict_slashes=False, methods=["POST"])
def synchronize():
    if _LOCK_SYNCHRONIZATION.acquire(blocking=False):
        threading.Thread(
            target=synchronization.synchronize,
            daemon=True,
            args=(_LOCK_SYNCHRONIZATION,),
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

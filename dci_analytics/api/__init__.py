# -*- coding: utf-8 -*-
#
# Copyright (C) Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import flask
from flask import json

import logging

logger = logging.getLogger(__name__)

api = flask.Blueprint("api", __name__)


@api.route("/ok", strict_slashes=False)
def index():
    logger.info("analytics server is ok...")
    return flask.Response(
        json.dumps({"_status": "OK", "message": "DCI Analytics"}),
        status=200,
        content_type="application/json",
    )


import dci_analytics.api.junit  # noqa
import dci_analytics.api.pipelines  # noqa
import dci_analytics.api.synchronization  # noqa

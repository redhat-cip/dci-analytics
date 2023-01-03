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
import logging

from dci_analytics import api
from dci_analytics import exceptions


app = flask.Flask(__name__)


logger = logging.getLogger()
formatter = logging.Formatter("%(levelname)s - %(message)s")
streamhandler = logging.StreamHandler()
streamhandler.setFormatter(formatter)
logger.addHandler(streamhandler)
logger.setLevel(logging.DEBUG)


def handle_api_exception(api_exception):
    response = flask.jsonify(api_exception.to_dict())
    response.status_code = api_exception.status_code
    logger.exception(api_exception)
    return response


app.register_error_handler(exceptions.DCIException, handle_api_exception)
app.register_blueprint(api.api)

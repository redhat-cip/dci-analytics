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

from dci_analytics import config
from dci_analytics.engine import logger
import requests

_ES_URL = config.CONFIG.get("ELASTICSEARCH_URL")
LOG = logger.get_logger()


def push(index, data, doc_id):
    res = requests.post("%s/%s/_create/%s" % (_ES_URL, index, doc_id), json=data)
    if res.status_code != 201:
        LOG.error(
            "error while pushing data to elastic index %s: %s" % (index, res.text)
        )

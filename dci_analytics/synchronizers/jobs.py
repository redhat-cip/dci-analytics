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

import logging

from dci.analytics import access_data_layer as a_d_l
from dci_analytics import elasticsearch as es
from dci_analytics import dci_db
from dci_analytics import config


logger = logging.getLogger(__name__)

_ES_URL = config.CONFIG.get("ELASTICSEARCH_URL")
_INDEX = "jobs"


def process(job):
    _id = job["id"]
    doc = es.get(_INDEX, _id)
    if not doc:
        es.push(_INDEX, job, _id)
    return job


def _sync(unit, amount):
    es.init_index(
        "jobs",
        json={
            "properties": {
                "team_id": {"type": "keyword"},
            }
        },
    )
    session_db = dci_db.get_session_db()
    limit = 100
    offset = 0

    offset = 0
    while True:
        jobs = a_d_l.get_jobs(session_db, offset, limit, unit=unit, amount=amount)
        if not jobs:
            break
        for job in jobs:
            try:
                logger.info("process job %s" % job["id"])
                process(job)
            except Exception as e:
                logger.error(
                    "error while processing job '%s': %s" % (job["id"], str(e))
                )
        offset += limit
    session_db.close()


def partial(_lock_synchronization):
    _sync("hours", 6)
    _lock_synchronization.release()


def full(_lock_synchronization):
    _sync("weeks", 12)
    _lock_synchronization.release()

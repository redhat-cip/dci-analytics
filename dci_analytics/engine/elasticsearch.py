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

import requests

from dci_analytics import config

_ES_URL = config.CONFIG.get("ELASTICSEARCH_URL")

logger = logging.getLogger(__name__)


def push(index, data, doc_id):
    url = "%s/%s/_create/%s" % (_ES_URL, index, doc_id)
    logger.debug(f"url: {url}")
    res = requests.post(url, json=data)
    if res.status_code != 201:
        logger.debug(
            "error while pushing data to elastic index %s: %s" % (index, res.text)
        )


def get(index, doc_id):
    url = "%s/%s/_doc/%s" % (_ES_URL, index, doc_id)
    logger.debug(f"url: {url}")
    res = requests.get(url)
    if res.status_code == 404:
        return None
    elif res.status_code == 200:
        return res.json()["_source"]
    else:
        logger.error(
            "error while getting document %s from index %s: %s"
            % (doc_id, index, res.text)
        )
        return None


def search(index, query=None, json=None):
    res = requests.get("%s/%s/_search?%s" % (_ES_URL, index, query))
    return res.json()["hits"]["hits"]


def search_json(index, json):
    res = requests.get("%s/%s/_search" % (_ES_URL, index), json=json)
    return res.json()["hits"]["hits"]


def update(index, data, doc_id):
    url = "%s/%s/_update/%s" % (_ES_URL, index, doc_id)
    logger.debug(f"url: {url}")
    res = requests.post(url, json={"doc": data})
    if res.status_code != 201 and res.status_code != 200:
        logger.error(
            "error while updating document %s to index %s: %s"
            % (doc_id, index, res.text)
        )


def init_index(index, json=None):
    url = "%s/%s" % (_ES_URL, index)
    result = requests.get(url)
    if result.status_code == 404:
        url = "%s/%s/_mapping" % (_ES_URL, index)
        if json:
            requests.put(url, json=json)
        else:
            requests.put(url)

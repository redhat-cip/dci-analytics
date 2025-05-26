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

from datetime import datetime as dt
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


def search(index, query=None):
    res = requests.get("%s/%s/_search?q=%s" % (_ES_URL, index, query))
    return res.json()


def search_json(index, json):
    res = requests.get("%s/%s/_search" % (_ES_URL, index), json=json)
    return res.json()


def update(index, data, doc_id):
    url = "%s/%s/_update/%s" % (_ES_URL, index, doc_id)
    logger.debug(f"url: {url}")
    res = requests.post(url, json={"doc": data})
    if res.status_code != 201 and res.status_code != 200:
        logger.error(
            "error while updating document %s to index %s: %s"
            % (doc_id, index, res.text)
        )


def get_autocompletion_values(index, team_id, field, is_admin=False, size=10):
    query = {
        "aggs": {"autocomplete": {"terms": {"field": field, "size": size}}},
        "size": 0,
    }
    if not is_admin:
        query["query"] = {"term": {"team_id": team_id}}

    res = search_json(index, query)
    return [f["key"] for f in res["aggregations"]["autocomplete"]["buckets"]]


def init_index(index, json=None):
    url = "%s/%s" % (_ES_URL, index)
    result = requests.get(url)
    if result.status_code == 404:
        requests.put("%s/%s" % (_ES_URL, index))
        url = "%s/%s/_mapping" % (_ES_URL, index)
        if json:
            requests.put(url, json=json)
        else:
            requests.put(url)


def update_index(index, json):
    is_index_created = False
    index_url = "%s/%s" % (_ES_URL, index)
    result = requests.get(index_url)
    if result.status_code != 200:
        r = requests.put(index_url, json=json).json()
        if "acknowledged" not in r:
            logger.error(str(r))
        is_index_created = True
    return is_index_created


def update_index_meta(index, first_job_date=None, last_job_date=None):
    url = "%s/%s/_mappings" % (_ES_URL, index)
    logger.debug(f"url: {url}")
    mappings = {"mappings": {"_meta": {}}}
    if first_job_date:
        mappings["mappings"]["_meta"]["first_sync_date"] = first_job_date
    if last_job_date:
        mappings["mappings"]["_meta"]["last_sync_date"] = last_job_date

    res = requests.put(url, json=mappings)
    if res.status_code != 201:
        logger.debug("error while updating index %s meta: %s" % (index, res.text))


def get_index_meta(index):
    url = "%s/%s/_mappings" % (_ES_URL, index)
    logger.debug(f"url: {url}")

    res = requests.get(url)
    if res.status_code != 200:
        logger.error("error while getting index mapping of %s: %s" % (index, res.text))
    return res.json()[index]["_mappings"]["_meta"]


def get_latest_index_alias(index_prefix):
    aliases_url = "%s/_cat/aliases?format=json" % _ES_URL
    result = requests.get(aliases_url)
    if result.status_code != 200:
        logger.error("error while getting aliases: %s" % result.text)
        return None
    result = result.json()
    if len(result) == 0:
        logger.debug("no aliases found")
        return None

    aliases = [a["alias"] for a in result if a["alias"].startswith(index_prefix)]
    aliases.sort()
    return aliases[-1]


def generate_new_index_name(index_prefix):
    now_timestamp = dt.now().timestamp()
    return f"{index_prefix}-{now_timestamp}"


def generate_new_alias_name(alias_prefix):
    now_iso_format = dt.now().isoformat()
    now_iso_format = now_iso_format.replace(":", "-")
    return f"{alias_prefix}-{now_iso_format}"


def add_alias_to_index(alias_prefix, index_name):
    alias_name = generate_new_alias_name(alias_prefix)
    alias_actions = {"actions": [{"add": {"index": index_name, "alias": alias_name}}]}
    requests.post(f"{_ES_URL}/_aliases", json=alias_actions)

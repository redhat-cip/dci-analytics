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
import datetime
import logging
import sys

import psycopg2
from psycopg2 import extras as pg_extras


from dci_analytics import config
from dci_analytics.engine.workers import tasks_duration_cumulated
from dci_analytics.engine.workers import tasks_components_coverage


logger = logging.getLogger(__name__)

_CONFIG = config.CONFIG
_WORKERS = [tasks_duration_cumulated, tasks_components_coverage]


def _format_field(record, prefix):
    res = {}
    for k, v in record.items():
        k_split = k.split("_", 1)
        if k_split[0] == prefix:
            res[k_split[1]] = v
            if (k_split[1] == "created_at" or k_split[1] == "updated_at") and v is None:
                return None
            if isinstance(v, datetime.datetime):
                res[k_split[1]] = v.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return res


def _format_jobs(jobs):
    res = {}
    js = {}
    cmpts = {}
    for j in jobs:
        if j["jobs_id"] not in res:
            res[j["jobs_id"]] = _format_field(j, "jobs")
            if not res[j["jobs_id"]]:
                continue
            if j["jobs_id"] not in cmpts:
                cmpts[j["jobs_id"]] = {}
        if "jobstates" not in res[j["jobs_id"]]:
            res[j["jobs_id"]]["jobstates"] = []
        jobstate = _format_field(j, "jobstates")
        if not jobstate:
            continue
        if jobstate["id"] not in js:
            js[jobstate["id"]] = jobstate
            res[j["jobs_id"]]["jobstates"].append(jobstate)
        js_file = _format_field(j, "files")
        if "files" not in js[jobstate["id"]]:
            js[jobstate["id"]]["files"] = []
        if js_file:
            js[jobstate["id"]]["files"].append(js_file)
        component = _format_field(j, "components")
        if not component:
            continue
        if "components" not in res[j["jobs_id"]]:
            res[j["jobs_id"]]["components"] = []
        if component["id"] not in cmpts[j["jobs_id"]]:
            cmpts[j["jobs_id"]][component["id"]] = component
            res[j["jobs_id"]]["components"].append(component)

    if not res:
        return []
    return list(res.values())


def get_db_connection():
    return psycopg2.connect(
        user=_CONFIG.get("POSTGRESQL_USER"),
        password=_CONFIG.get("POSTGRESQL_PASSWORD"),
        host=_CONFIG.get("POSTGRESQL_HOST"),
        port=_CONFIG.get("POSTGRESQL_PORT"),
        database=_CONFIG.get("POSTGRESQL_DATABASE"),
    )


def _get_table_columns_names(db_conn, table_name):
    with db_conn.cursor(cursor_factory=pg_extras.DictCursor) as cursor:
        try:
            cursor.execute("SELECT * from %s LIMIT 0;" % table_name)
            return [d.name for d in cursor.description]
        except Exception as err:
            print("psycopg2 error: %s" % str(err))
            sys.exit(1)


def get_jobs(db_conn, offset, limit, unit="hours", amount=2):
    jobs_columns_names = _get_table_columns_names(db_conn, "jobs")
    jobs_aliases_1 = ["jobs_%s" % n for n in jobs_columns_names]
    jobs_aliases_2 = ["jobs.%s as jobs_%s" % (n, n) for n in jobs_columns_names]
    jobstates_columns_names = _get_table_columns_names(db_conn, "jobstates")
    jobstates_aliases = [
        "jobstates.%s as jobstates_%s" % (n, n) for n in jobstates_columns_names
    ]
    files_columns_names = _get_table_columns_names(db_conn, "files")
    files_aliases = ["files.%s as files_%s" % (n, n) for n in files_columns_names]
    components_columns_names = _get_table_columns_names(db_conn, "components")
    components_aliases = [
        "components.%s as components_%s" % (n, n) for n in components_columns_names
    ]

    with db_conn.cursor(cursor_factory=pg_extras.DictCursor) as cursor:
        query = """
        SELECT {jobs_aliases_1}, {jobstates_aliases}, {files_aliases}, {components_aliases}
        FROM
        (SELECT {jobs_aliases_2}
          FROM JOBS
          WHERE JOBS.state = 'active' AND (JOBS.created_at > (current_timestamp - make_interval({unit} => {amount}))) AND JOBS.status IN ('success', 'failure')
          ORDER BY JOBS.created_at ASC
          LIMIT  {limit}
          OFFSET {offset}) AS JOBS
        LEFT OUTER JOIN JOBSTATES ON JOBSTATES.job_id = jobs_id
        LEFT OUTER JOIN FILES ON FILES.jobstate_id = JOBSTATES.id
        LEFT OUTER JOIN JOBS_COMPONENTS on JOBS_COMPONENTS.job_id = jobs_id
        LEFT OUTER JOIN COMPONENTS on JOBS_COMPONENTS.component_id = COMPONENTS.id
        ORDER BY JOBSTATES.created_at ASC
        """.format(
            jobs_aliases_1=", ".join(jobs_aliases_1),
            jobs_aliases_2=", ".join(jobs_aliases_2),
            jobstates_aliases=", ".join(jobstates_aliases),
            files_aliases=", ".join(files_aliases),
            components_aliases=", ".join(components_aliases),
            limit=limit,
            offset=offset,
            unit=unit,
            amount=amount,
        )
        try:
            cursor.execute(query)
            jobs = [dict(j) for j in cursor.fetchall()]
        except Exception as err:
            print("error: %s" % str(err))
            sys.exit(1)
    return _format_jobs(jobs)


def _format_components(components):
    res = {}
    for c in components:
        if c["components_id"] not in res:
            res[c["components_id"]] = _format_field(c, "components")
            if not res[c["components_id"]]:
                continue
    if not res:
        return []
    return list(res.values())


def get_components(db_conn, offset, limit, unit="hours", amount=2):
    components_columns_names = _get_table_columns_names(db_conn, "components")
    components_aliases = [
        "components.%s as components_%s" % (n, n) for n in components_columns_names
    ]

    with db_conn.cursor(cursor_factory=pg_extras.DictCursor) as cursor:
        query = """
        SELECT {components_aliases}
        FROM COMPONENTS
        WHERE COMPONENTS.state = 'active' AND (COMPONENTS.created_at > (current_timestamp - make_interval({unit} => {amount})))
        ORDER BY COMPONENTS.created_at ASC
        LIMIT  {limit}
        OFFSET {offset}
        """.format(
            components_aliases=", ".join(components_aliases),
            limit=limit,
            offset=offset,
            unit=unit,
            amount=amount,
        )
        try:
            cursor.execute(query)
            components = [dict(j) for j in cursor.fetchall()]
        except Exception as err:
            print("error: %s" % str(err))
            sys.exit(1)
    return _format_components(components)

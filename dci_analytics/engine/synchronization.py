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
from dci_analytics.engine.workers import task_duration_cumulated


logger = logging.getLogger(__name__)

_CONFIG = config.CONFIG


def format_field(record, prefix):
    res = {}
    for k, v in record.items():
        k_split = k.split("_", 1)
        if k_split[0] == prefix:
            res[k_split[1]] = v
            if isinstance(v, datetime.datetime):
                res[k_split[1]] = v.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return res


def format(records):
    res = {}
    js = {}
    for r in records:
        if r["jobs_id"] not in res:
            res[r["jobs_id"]] = format_field(r, "jobs")
        if "jobstates" not in res[r["jobs_id"]]:
            res[r["jobs_id"]]["jobstates"] = []
        jobstate = format_field(r, "jobstates")
        if jobstate["id"] not in js:
            js[jobstate["id"]] = jobstate
            res[r["jobs_id"]]["jobstates"].append(jobstate)
        js_file = format_field(r, "files")
        if "files" not in js[jobstate["id"]]:
            js[jobstate["id"]]["files"] = []
        js[jobstate["id"]]["files"].append(js_file)
    return list(res.values())


def get_db_connection():
    return psycopg2.connect(
        user=_CONFIG.get("POSTGRESQL_USER"),
        password=_CONFIG.get("POSTGRESQL_PASSWORD"),
        host=_CONFIG.get("POSTGRESQL_HOST"),
        port=_CONFIG.get("POSTGRESQL_PORT"),
        database=_CONFIG.get("POSTGRESQL_DATABASE"),
    )


def get_table_columns_names(db_conn, table_name):
    with db_conn.cursor(cursor_factory=pg_extras.DictCursor) as cursor:
        try:
            cursor.execute("SELECT * from %s;" % table_name)
            return [d.name for d in cursor.description]
        except Exception as err:
            print("psycopg2 error: %s" % str(err))
            sys.exit(1)


def get_jobs(db_conn):
    jobs_columns_names = get_table_columns_names(db_conn, "jobs")
    jobs_aliases = ["jobs.%s as jobs_%s" % (n, n) for n in jobs_columns_names]
    jobstates_columns_names = get_table_columns_names(db_conn, "jobstates")
    jobstates_aliases = [
        "jobstates.%s as jobstates_%s" % (n, n) for n in jobstates_columns_names
    ]
    files_columns_names = get_table_columns_names(db_conn, "files")
    files_aliases = ["files.%s as files_%s" % (n, n) for n in files_columns_names]
    query = "SELECT %s, %s, %s from JOBS INNER JOIN JOBSTATES on (JOBSTATES.job_id = JOBS.id) INNER JOIN FILES on (FILES.jobstate_id = JOBSTATES.id) WHERE (JOBS.created_at > (current_timestamp - make_interval(mins => 120)) AND JOBS.status IN ('success', 'failure')) ORDER BY JOBSTATES.created_at ASC;"
    query = query % (
        ", ".join(jobs_aliases),
        ", ".join(jobstates_aliases),
        ", ".join(files_aliases),
    )
    with db_conn.cursor(cursor_factory=pg_extras.DictCursor) as cursor:
        try:
            cursor.execute(query)
            jobs = [dict(j) for j in cursor.fetchall()]
            return format(jobs)
        except Exception as err:
            print("psycopg2 error: %s" % str(err))
            sys.exit(1)


def synchronize(_lock_synchronization):
    db_connection = get_db_connection()
    jobs = get_jobs(db_connection)

    for job in jobs:
        logger.info("process job %s" % job["id"])
        task_duration_cumulated.process(job)

    _lock_synchronization.release()

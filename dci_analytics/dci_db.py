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

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from dci_analytics import config


def get_session_db():
    _CONFIG = config.CONFIG
    uri = "postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}".format(
        db_user=_CONFIG.get("POSTGRESQL_USER"),
        db_password=_CONFIG.get("POSTGRESQL_PASSWORD"),
        db_host=_CONFIG.get("POSTGRESQL_HOST"),
        db_port=_CONFIG.get("POSTGRESQL_PORT"),
        db_name=_CONFIG.get("POSTGRESQL_DATABASE"),
    )

    return sessionmaker(
        bind=sqlalchemy.create_engine(
            uri,
            pool_size=5,
            max_overflow=25,
            encoding="utf8",
            convert_unicode=True,
            echo=False,
        )
    )()

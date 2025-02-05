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
import os


logger = logging.getLogger(__name__)


def get_config():
    _config = {
        "ELASTICSEARCH_URL": os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"),
        "POSTGRESQL_USER": os.getenv("POSTGRESQL_USER", "dci"),
        "POSTGRESQL_PASSWORD": os.getenv("POSTGRESQL_PASSWORD", "dci"),
        "POSTGRESQL_HOST": os.getenv("POSTGRESQL_HOST", "127.0.0.1"),
        "POSTGRESQL_PORT": os.getenv("POSTGRESQL_PORT", "5432"),
        "POSTGRESQL_DATABASE": os.getenv("POSTGRESQL_DATABASE", "dci"),
        "DCI_LOGIN": os.getenv("DCI_LOGIN", "admin"),
        "DCI_CLIENT_ID": os.getenv("DCI_CLIENT_ID", ""),
        "DCI_API_SECRET": os.getenv("DCI_API_SECRET", ""),
        "DCI_CS_URL": os.getenv("DCI_CS_URL", "http://api:5000"),
    }

    return _config


CONFIG = get_config()

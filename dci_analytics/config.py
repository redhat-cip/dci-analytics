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

from dci_analytics.engine import logger

import os

LOG = logger.get_logger()


def get_config():

    _config = {
        "ELASTICSEARCH_URL": os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"),
        "POSTGRESQL_USER": os.getenv("POSTGRESQL_USER", "dci"),
        "POSTGRESQL_PASSWORD": os.getenv("POSTGRESQL_PASSWORD", "dci"),
        "POSTGRESQL_HOST": os.getenv("POSTGRESQL_HOST", "127.0.0.1"),
        "POSTGRESQL_PORT": os.getenv("POSTGRESQL_PORT", "5432"),
    }
    _debug_config = dict(_config)
    _debug_config["POSTGRESQL_PASSWORD"] = "NA"
    LOG.debug(_debug_config)
    return _config


CONFIG = get_config()

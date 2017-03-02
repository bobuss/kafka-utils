# -*- coding: utf-8 -*-
# Copyright 2016 Yelp Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
from functools import partial

from fabric.api import execute
from fabric.api import hide
from fabric.api import settings
from fabric.api import sudo
from fabric.api import task

from .precheck import Precheck
from .precheck import PrecheckFailedException


KAFKA_UPDATE_CMD = "run-puppet"
DEFAULT_CONFIG_FILE_LOCATION = "/etc/kafka/server.properties"


class ConfigPrecheck(Precheck):
    """Class to check for kafka configs"""

    def parse_args(self, args):
        parser = argparse.ArgumentParser(prog='ConfigPrecheck')
        parser.add_argument(
            '--ensure-configs',
            type=str,
            required=True,
            help='kafka configs which need to be ensured to be present',
        )
        parser.add_argument(
            '--config-file',
            type=str,
            default=DEFAULT_CONFIG_FILE_LOCATION,
            help='location of the config file',
        )
        return parser.parse_args(args)

    @task
    def _execute_cmd(self, cmd):
        """Execute the command, and return the output"""
        with hide('output', 'running', 'warnings'), settings(warn_only=True):
            return sudo(cmd)

    def _execute_package_update(self, cmd, host):
        """Execute preconditions before restarting broker"""
        print("Attempting to get latest package")
        execute_package_update_func = partial(
            self._execute_cmd,
            ConfigPrecheck,
            KAFKA_UPDATE_CMD,
        )
        execute(execute_package_update_func, hosts=host)

    def _assert_configs_present(self, host):
        '''Check if the configs are present on the host'''
        cmd = 'cat ' + self.args.config_file
        configs = set(self.args.ensure_configs.split(','))
        execute_cmd_func = partial(
            self._execute_cmd,
            ConfigPrecheck,
            cmd,
        )
        output = execute(execute_cmd_func, hosts=host).get(host)
        config_on_host = set(output.split('\r\n'))
        config_present = configs.issubset(config_on_host)
        if not config_present:
            raise PrecheckFailedException

    def run(self, host):
        self._assert_configs_present(host)

    def success(self, host):
        print("Precheck for configs is successfull")

    def failure(self, host):
        print("WARN: Precheck failed for configs")
        self._execute_package_update(KAFKA_UPDATE_CMD, host)

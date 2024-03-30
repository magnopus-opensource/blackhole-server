# Copyright 2024 Magnopus

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
import configparser
import shutil
from blackhole.constants import *

def app_config_valid():
    config_path = pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME)

    if not config_path.exists():
        return False
    else:
        archive_header = "ArchiveSettings"
        archive_keys = ["ARCHIVE_DIRECTORY", "DATABASE_PATH", "MASTER_SPREADSHEET_PATH"]
        
        export_header = "ExportSettings"
        export_keys = ["EXPORT_DIRECTORY"]

        parser = configparser.ConfigParser()
        parser.read(config_path)

        if archive_header not in parser:
            return False
        elif not all(key in parser[archive_header].keys() for key in archive_keys):
            return False
        elif export_header not in parser:
            return False
        elif not all(key in parser[export_header].keys() for key in export_keys):
            return False
        
        return True
        
def device_config_valid():
    config_path = pathlib.Path(CONFIG_DIR, DEVICE_CONFIG_NAME)

    if not config_path.exists():
        return False
    else:
        device_keys = ["IP_ADDRESS", "PORT", "TRACKING_PROTOCOL"]

        parser = configparser.ConfigParser()
        parser.read(config_path)

        for section in parser.sections():
            if not all(key in parser[section].keys() for key in device_keys):
                return False
        
        return True

def initialize():
    default_config_dir = pathlib.Path(__file__).resolve().parent / "default_config"
    config_dir = pathlib.Path(CONFIG_DIR).resolve()
    config_dir.mkdir(parents = True, exist_ok = True)

    if not app_config_valid():
        default_app_config_path = default_config_dir / "default_app_config.ini"
        app_config_path = config_dir / APP_CONFIG_NAME
        shutil.copy(default_app_config_path,app_config_path)

    if not device_config_valid():
        default_device_config_path = default_config_dir / "default_device_config.ini"        
        device_config_path = config_dir / DEVICE_CONFIG_NAME
        shutil.copy(default_device_config_path, device_config_path)
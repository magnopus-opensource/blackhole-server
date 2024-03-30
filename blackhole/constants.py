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

# Tracking Constants
TRACKING_X = "XPos"
TRACKING_Y = "YPos"
TRACKING_Z = "ZPos"
TRACKING_PAN = "Pan"
TRACKING_ROLL = "Roll"
TRACKING_TILT = "Tilt"
TRACKING_PITCH = "Pitch"
TRACKING_YAW = "Yaw"
TRACKING_ASPECT_RATIO = "AspectRatio"
TRACKING_FOCUS = "Focus"
TRACKING_ZOOM = "Zoom"
TRACKING_FOV = "FOV"
TRACKING_FOCALLENGTH = "FocalLength"
TRACKING_TIMECODE_IN = "TimecodeIn"
TRACKING_TIMECODE_OUT = "TimecodeOut"
TRACKING_TIMECODE_KEY = "TimecodeKey"
TRACKING_TIMECODE_HOUR = "TimecodeHour"
TRACKING_TIMECODE_MINUTES = "TimecodeMinutes"
TRACKING_TIMECODE_SECONDS = "TimecodeSeconds"
TRACKING_TIMECODE_FRAMES = 'TimecodeFrames'

# Config Path Strings
CONFIG_DIR = "blackhole_config"
APP_CONFIG_NAME = "app_config.ini"
DEVICE_CONFIG_NAME = "device_config.ini"

# Database Main Table
MAIN_TABLE_NAME = "blackhole_takes"

# Database Column Labels
SLATE_DB_COL = "slate"
TAKE_NUMBER_DB_COL = "take_number"
CORRECTED_SLATE_DB_COL = "corrected_slate"
CORRECTED_TAKE_DB_COL = "corrected_take_number"
VALID_DB_COL = "valid"
DATE_DB_COL = "date"
USD_ARCHIVE_DB_COL = "usd_archive_location"
DESCRIPTION_DB_COL = "description"
FRAME_RATE_DB_COL = "frame_rate"
TIMECODE_IN_FRAMES_DB_COL = "timecode_in_frames"
TIMECODE_OUT_FRAMES_DB_COL = "timecode_out_frames"
TIMECODE_IN_SMPTE_DB_COL = "timecode_in_smpte"
TIMECODE_OUT_SMPTE_DB_COL = "timecode_out_smpte"
LEVEL_SNAPSHOT_DB_COL = "level_snapshot_location"
LEVEL_SEQUENCE_DB_COL = "level_sequence_location"
MAP_DB_COL = "map"

SHOT_DB_SCHEMA = [
    SLATE_DB_COL,
    TAKE_NUMBER_DB_COL,
    CORRECTED_SLATE_DB_COL,
    CORRECTED_TAKE_DB_COL,
    VALID_DB_COL,
    DATE_DB_COL,
    FRAME_RATE_DB_COL,
    TIMECODE_IN_FRAMES_DB_COL,
    TIMECODE_OUT_FRAMES_DB_COL,
    TIMECODE_IN_SMPTE_DB_COL,
    TIMECODE_OUT_SMPTE_DB_COL,
    LEVEL_SNAPSHOT_DB_COL,
    LEVEL_SEQUENCE_DB_COL,
    MAP_DB_COL,
    USD_ARCHIVE_DB_COL,
    DESCRIPTION_DB_COL
]

def schemaLabelToTitle(columnName : str) -> str:
    tokens = columnName.split("_")
    upper = []

    for token in tokens:
        if token == 'smpte':
            upper.append('SMPTE')
        else:
            upper.append(token.title())

    title = str.join(" ", upper)
    return title

# Take Search Criteria Labels
START_DATE_FILTER = "start_date"
END_DATE_FILTER = "end_date"
SLATE_HINT_FILTER = "slate_hint"
FRAME_RATE_FILTER = "frame_rate"



# Spreadsheet Constants
HEADER_COLOR = "878787"
VALID_COLOR = "69BF80"
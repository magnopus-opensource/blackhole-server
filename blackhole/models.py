# Copyright 2024 Magnopus LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import date

from pydantic import BaseModel, Field

from blackhole.constants import *


class TakeCreation(BaseModel):
    slate: str = Field(min_length=1, alias=SLATE_DB_COL)
    take_number: int = Field(gt=0, alias=TAKE_NUMBER_DB_COL)
    date_created: date = Field(alias=DATE_DB_COL)
    valid: bool = Field(default=False, alias=VALID_DB_COL)
    description: str | None = Field(default=None, alias=DESCRIPTION_DB_COL)
    frame_rate: int | None = Field(default=None, gt=0, alias=FRAME_RATE_DB_COL)
    timecode_in_frames: int | None = Field(default=None, gt=0, alias=TIMECODE_IN_FRAMES_DB_COL)
    timecode_out_frames: int | None = Field(default=None, gt=0, alias=TIMECODE_OUT_FRAMES_DB_COL)
    timecode_in_smpte: str | None = Field(default=None, alias=TIMECODE_IN_SMPTE_DB_COL)
    timecode_out_smpte: str | None = Field(default=None, alias=TIMECODE_OUT_SMPTE_DB_COL)
    level_snapshot_location: str | None = Field(default=None, alias=LEVEL_SNAPSHOT_DB_COL)
    level_sequence_location: str | None = Field(default=None, alias=LEVEL_SEQUENCE_DB_COL)
    map: str | None = Field(default=None, alias=MAP_DB_COL)

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'slate': 'TEST-1A',
                    'take_number': 1,
                    'date_created': '2023-01-01',
                    'description': 'This is an example description.',
                    'valid': True,
                    'frame_rate': 24,
                    'timecode_in_frames': 10000,
                    'timecode_out_frames': 20000,
                    'timecode_in_smpte': '00:06:56:15',
                    'timecode_out_smpte': '00:13:53:07',
                    'level_snapshot_location': 'Cinematics/LevelSnapshots/ExampleLevelSnapshots',
                    'level_sequence_location': 'Cinematics/LevelSequences/TestLevelSequences',
                    'map': 'ExampleMap_1',
                }
            ]
        }
    }


# You are not allowed to update the date of a take in the database, so the date field
# is not part of the TakeUpdate mode.
class TakeUpdate(BaseModel):
    slate: str = Field(min_length=1, alias=SLATE_DB_COL)
    take_number: int = Field(gt=0, alias=TAKE_NUMBER_DB_COL)
    description: str | None = Field(default=None, alias=DESCRIPTION_DB_COL)
    valid: bool | None = Field(default=None, alias=VALID_DB_COL)
    frame_rate: int | None = Field(default=None, gt=0, alias=FRAME_RATE_DB_COL)
    timecode_in_frames: int | None = Field(default=None, gt=0, alias=TIMECODE_IN_FRAMES_DB_COL)
    timecode_out_frames: int | None = Field(default=None, gt=0, alias=TIMECODE_OUT_FRAMES_DB_COL)
    timecode_in_smpte: str | None = Field(default=None, alias=TIMECODE_IN_SMPTE_DB_COL)
    timecode_out_smpte: str | None = Field(default=None, alias=TIMECODE_OUT_SMPTE_DB_COL)
    level_snapshot_location: str | None = Field(default=None, alias=LEVEL_SNAPSHOT_DB_COL)
    level_sequence_location: str | None = Field(default=None, alias=LEVEL_SEQUENCE_DB_COL)
    map: str | None = Field(default=None, alias=MAP_DB_COL)
    usd_export_location: str | None = Field(default=None, alias=USD_ARCHIVE_DB_COL)

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'slate': 'TEST-1A',
                    'take_number': 1,
                    'description': 'This is an example description.',
                    'valid': True,
                    'frame_rate': 24,
                    'timecode_in_frames': 10000,
                    'timecode_out_frames': 20000,
                    'timecode_in_smpte': '00:06:56:15',
                    'timecode_out_smpte': '00:13:53:07',
                    'level_snapshot_location': 'Cinematics/LevelSnapshots/ExampleLevelSnapshots',
                    'level_sequence_location': 'Cinematics/LevelSequences/TestLevelSequences',
                    'map': 'ExampleMap_1',
                }
            ]
        }
    }


class Take(BaseModel):
    slate: str = Field(min_length=1, alias=SLATE_DB_COL)
    take_number: int = Field(gt=0, alias=TAKE_NUMBER_DB_COL)
    date_created: date = Field(alias=DATE_DB_COL)
    description: str | None = Field(default=None, alias=DESCRIPTION_DB_COL)
    valid: bool = Field(default=False, alias=VALID_DB_COL)
    frame_rate: int | None = Field(default=None, gt=0, alias=FRAME_RATE_DB_COL)
    timecode_in_frames: int | None = Field(default=None, gt=0, alias=TIMECODE_IN_FRAMES_DB_COL)
    timecode_out_frames: int | None = Field(default=None, gt=0, alias=TIMECODE_OUT_FRAMES_DB_COL)
    timecode_in_smpte: str | None = Field(default=None, alias=TIMECODE_IN_SMPTE_DB_COL)
    timecode_out_smpte: str | None = Field(default=None, alias=TIMECODE_OUT_SMPTE_DB_COL)
    level_snapshot_location: str | None = Field(default=None, alias=LEVEL_SNAPSHOT_DB_COL)
    level_sequence_location: str | None = Field(default=None, alias=LEVEL_SEQUENCE_DB_COL)
    map: str | None = Field(default=None, alias=MAP_DB_COL)
    usd_export_location: str | None = Field(default=None, alias=USD_ARCHIVE_DB_COL)

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'slate': 'TEST-1A',
                    'take_number': 1,
                    'date_created': '2023-01-01',
                    'description': 'This is an example description.',
                    'valid': True,
                    'frame_rate': 24,
                    'timecode_in_frames': 10000,
                    'timecode_out_frames': 20000,
                    'timecode_in_smpte': '00:06:56:15',
                    'timecode_out_smpte': '00:13:53:07',
                    'level_snapshot_location': 'Cinematics/LevelSnapshots/ExampleLevelSnapshots',
                    'level_sequence_location': 'Cinematics/LevelSequences/TestLevelSequences',
                    'map': 'ExampleMap_1',
                    'usd_export_location': 'ExampleArchive/ExampleSlate/1'
                }
            ]
        }
    }


class TakeIDsList(BaseModel):
    id_list: list[tuple[str, int]]
    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'id_list': [
                        ["SlateA", 1],
                        ["SlateB", 2],
                        ["SlateC", 3]
                    ],
                }
            ]
        }
    }

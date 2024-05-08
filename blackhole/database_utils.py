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

import configparser
import logging
import pathlib
import shutil
import sqlite3
from datetime import datetime

from timecode import Timecode

from blackhole.models import *
from blackhole.sheets import SpreadsheetWriter

logger = logging.getLogger(__name__)


def get_system_timecode_as_frames(frame_rate: int):
    """
    Get the current timecode as a frame count, derived from system time. Must be provided a frame rate. 

    :return The current system time as a frame count. Will account for drop-frame timecodes.
    :rtype int

    """
    system_time = datetime.now()

    system_time_seconds = ((system_time.hour * 60 + system_time.minute) * 60 + system_time.second
                           + system_time.microsecond)

    timecode = Timecode(frame_rate, start_seconds=system_time_seconds)
    return timecode.frames


def frames_to_smpte(frame_rate: int, frames_to_convert: int) -> str:
    """
    Takes the given frame rate and number of frames and returns the SMPTE
    timecode string representing that frame count at that frame rate.

    :return The timecode representation as an SMPTE-style string.
    :rtype string
    """
    timecode = Timecode(frame_rate, frames=frames_to_convert)
    return repr(timecode)


def get_database_path() -> str:
    app_config_parser = configparser.ConfigParser()
    app_config_parser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))

    database_path = pathlib.Path(app_config_parser["ArchiveSettings"]["DATABASE_PATH"])

    database_path.resolve(strict=False).parent.mkdir(parents=True, exist_ok=True)
    database_path.touch()

    return str(database_path)


def get_export_path() -> str:
    app_config_parser = configparser.ConfigParser()
    app_config_parser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))

    export_path = pathlib.Path(app_config_parser["ExportSettings"]["EXPORT_DIRECTORY"])

    export_path.resolve(strict=False).mkdir(parents=True, exist_ok=True)

    return str(export_path)


def initialize_database():
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        try:
            # Create the database if it doesn't already exist
            dbConnection.execute(
                f"CREATE TABLE IF NOT EXISTS {MAIN_TABLE_NAME} "
                "( "
                f"{SLATE_DB_COL} TEXT NOT NULL, "
                f"{TAKE_NUMBER_DB_COL} INT NOT NULL, "
                f"{CORRECTED_SLATE_DB_COL} TEXT, "
                f"{CORRECTED_TAKE_DB_COL} INT, "
                f"{VALID_DB_COL} INT NOT NULL DEFAULT 0, "
                f"{DATE_DB_COL} TEXT NOT NULL, "
                f"{FRAME_RATE_DB_COL} INT, "
                f"{TIMECODE_IN_FRAMES_DB_COL} INT, "
                f"{TIMECODE_OUT_FRAMES_DB_COL} INT, "
                f"{TIMECODE_IN_SMPTE_DB_COL} TEXT, "
                f"{TIMECODE_OUT_SMPTE_DB_COL} TEXT, "
                f"{LEVEL_SNAPSHOT_DB_COL} TEXT, "
                f"{LEVEL_SEQUENCE_DB_COL} TEXT, "
                f"{MAP_DB_COL} TEXT, "
                f"{USD_ARCHIVE_DB_COL} TEXT, "
                f"{DESCRIPTION_DB_COL} TEXT, "
                f"PRIMARY KEY ({SLATE_DB_COL}, {TAKE_NUMBER_DB_COL}) "
                ")"
            )

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.initializeDatabase() SQLite Error: {e}")


def get_master_spreadsheet_path() -> str:
    app_config_parser = configparser.ConfigParser()
    app_config_parser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))
    spreadsheet_path = pathlib.Path(app_config_parser["ArchiveSettings"]["MASTER_SPREADSHEET_PATH"])

    return str(spreadsheet_path.resolve(strict=False))


def update_master_spreadsheet(slate, take_number):
    take_data = retrieve_take(slate, take_number)
    spreadsheet_writer = SpreadsheetWriter(get_master_spreadsheet_path())
    spreadsheet_writer.add_or_update_take(take_data)


def get_base_archive_path() -> str:
    app_config_parser = configparser.ConfigParser()
    app_config_parser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))

    base_archive_path = pathlib.Path(app_config_parser["ArchiveSettings"]["ARCHIVE_DIRECTORY"])
    return str(base_archive_path.resolve(strict=False))


def check_take_exists(slate: str, take_number: int) -> bool:
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = {f"{SLATE_DB_COL}": slate, f"{TAKE_NUMBER_DB_COL}": take_number}

            command = (f"SELECT 1 FROM {MAIN_TABLE_NAME} WHERE {SLATE_DB_COL} = :{SLATE_DB_COL} AND "
                       f"{TAKE_NUMBER_DB_COL} = :{TAKE_NUMBER_DB_COL}")
            cursor.execute(command, query)

            if cursor.fetchone():
                return True
            else:
                return False

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.checkRowExists() SQLite Error: {e}")

        finally:
            cursor.close()


def retrieve_take(slate: str, take_number: int) -> Take | None:
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = {f"{SLATE_DB_COL}": slate, f"{TAKE_NUMBER_DB_COL}": take_number}

            command = (f"SELECT * FROM {MAIN_TABLE_NAME} WHERE {SLATE_DB_COL} = :{SLATE_DB_COL} AND "
                       f"{TAKE_NUMBER_DB_COL} = :{TAKE_NUMBER_DB_COL}")
            cursor.execute(command, query)

            row = cursor.fetchone()

            if row:
                return Take(**dict(row))
            else:
                return None

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.retrieveDataRow() SQLite Error: {e}")

        finally:
            cursor.close()


def retrieve_takes(start_date=None, end_date=None, slate_hint=None) -> list[Take]:
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            command = f"SELECT * FROM {MAIN_TABLE_NAME}"

            query = {
                START_DATE_FILTER: start_date,
                END_DATE_FILTER: end_date,
            }

            # Adding SQL wildcard character to slate hint to indicate it should be
            # treated as the beginning substring of any eligible slate names 
            if slate_hint is not None:
                query[SLATE_HINT_FILTER] = slate_hint + "%"

            filter_commands = []

            if start_date is not None:
                filter_commands.append(f'{DATE_DB_COL} >= :{START_DATE_FILTER}')

            if end_date is not None:
                filter_commands.append(f'{DATE_DB_COL} <= :{END_DATE_FILTER}')

            if slate_hint is not None:
                filter_commands.append(f'{SLATE_DB_COL} LIKE :{SLATE_HINT_FILTER}')

            if len(filter_commands) > 0:
                command = command + ' WHERE ' + str.join(' AND ', filter_commands)

            cursor.execute(command, query)

            raw_results = cursor.fetchall()
            results = [Take(**dict(row)) for row in raw_results]

            return results

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.retrieveAllRows() SQLite Error: {e}")
            return []

        finally:
            cursor.close()


def retrieve_takes_by_list(slate_and_take_list: TakeIDsList, include_corrections=True) -> list[Take]:
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            list_as_sql_string = ", ".join([f'("{t[0]}", {t[1]})' for t in slate_and_take_list.id_list])

            command = (f"SELECT * FROM blackhole_takes WHERE ({SLATE_DB_COL}, {TAKE_NUMBER_DB_COL}) IN "
                       f"({list_as_sql_string})")

            if include_corrections:
                command += f" OR ({CORRECTED_SLATE_DB_COL}, {CORRECTED_TAKE_DB_COL}) IN ({list_as_sql_string})"

            cursor.execute(command)

            raw_results = cursor.fetchall()
            results = [Take(**dict(row)) for row in raw_results]

            return results

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.retrieveTakesByList() SQLite Error: {e}")

        finally:
            cursor.close()


def update_take(take_update: TakeUpdate) -> Take | None:
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = take_update.model_dump(by_alias=True, exclude_none=True)

            update_command = f"UPDATE {MAIN_TABLE_NAME} SET "
            set_values = []
            for key in query.keys():
                if key not in (SLATE_DB_COL, TAKE_NUMBER_DB_COL):
                    set_values.append(f"{key} = :{key}")

            if len(set_values) == 0:
                logger.warning("The dictionary given to BlackholeLibrary.updateData() does not contain any values to "
                               "update. Skipping.")
                return

            update_command += ", ".join(set_values)
            update_command += (f" WHERE {SLATE_DB_COL} = :{SLATE_DB_COL} "
                               f"AND {TAKE_NUMBER_DB_COL} = :{TAKE_NUMBER_DB_COL}")

            cursor.execute(update_command, query)
            dbConnection.commit()

            update_master_spreadsheet(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])
            return retrieve_take(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.updateRow() SQLite Error: {e}")
            return None

        finally:
            cursor.close()


def insert_take(new_take: TakeCreation) -> Take | None:
    database_path = get_database_path()

    with sqlite3.connect(database_path) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = new_take.model_dump(by_alias=True, exclude_none=True)

            command = f"INSERT INTO {MAIN_TABLE_NAME}"
            placeholder_list = []
            for key in query.keys():
                placeholder_list.append(":" + key)

            columns = ", ".join(query.keys())
            placeholders = ", ".join(placeholder_list)

            command += f" ({columns}) VALUES ({placeholders})"

            cursor.execute(command, query)
            dbConnection.commit()

            update_master_spreadsheet(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])
            return retrieve_take(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.insertRow() SQLite Error: {e}")
            return None

        except sqlite3.IntegrityError as e:
            logger.error(f"blackhole.lib.insertRow() SQLite Error: {e}")
            return None

        finally:
            cursor.close()


def copy_to_export_directory(takes: list[Take]) -> tuple[str, list[Take], list[Take]]:
    export_base_path = pathlib.Path(get_export_path())

    # New export directory is named with a datetime string
    format_string = "%Y-%m-%d_%H-%M-%S"
    now_string = datetime.now().strftime(format_string)

    new_export_directory = export_base_path / now_string
    new_export_directory.mkdir()

    # Create a new spreadsheet writer pointed at the new export directory
    export_spreadsheet_path = pathlib.Path(new_export_directory, now_string + ".xlsx")
    spreadsheet_writer = SpreadsheetWriter(export_spreadsheet_path)

    success_exports = []
    failed_exports = []
    for take in takes:
        if take.usd_export_location:

            # We store the archive paths of our USDs as absolute, but for the 
            # export spreadsheet it's better to switch to relative paths
            usd_archive_path = pathlib.Path(take.usd_export_location)
            archive_path_stem = usd_archive_path.relative_to(get_base_archive_path())

            usd_export_path = new_export_directory / archive_path_stem

            shutil.copytree(usd_archive_path, usd_export_path)

            # Write our take data to the export spreadsheet, making sure to update the USD path
            # to the new location
            export_take = take.model_copy(deep=True)
            export_take.usd_export_location = str(pathlib.Path(now_string, archive_path_stem))
            spreadsheet_writer.add_or_update_take(export_take, create_backup=False)

            success_exports.append(export_take)
        else:
            failed_exports.append(take)
            logger.warning(f"Take for Slate: {take.slate}, Take Number: {take.take_number} has no USD to export!")

    # Create zip file from the new export directory we've made
    zip_name = shutil.make_archive(new_export_directory, 'zip', new_export_directory)

    # Delete the directory now that it's zipped to save space
    shutil.rmtree(new_export_directory)

    # Return the path to the new zip as a string
    return zip_name, success_exports, failed_exports

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

from timecode import Timecode
from datetime import datetime, date
import sqlite3
import pathlib
import configparser
import shutil
import logging
from blackhole.constants import *
from blackhole.sheets import SpreadsheetWriter
from blackhole.models import *

logger = logging.getLogger(__name__)

def getSystemTimecodeAsFrames(frameRate : int):
    """
    Get the current timecode derived from system time. Must be provided a frame rate. 

    :return The timecode representation as both frames and as a SMPTE-style string.
    :rtype tuple

    """
    systemTime = datetime.now()
    
    secondsFraction = float(systemTime.strftime(("%f"))) / 1000000.0
    frame = int(secondsFraction * float(frameRate))

    truncatedTime = systemTime.strftime("%X")
    timecodeString = "{0}:{1}".format(truncatedTime, frame)

    timecode = Timecode(frameRate, timecodeString)
    return timecode.frames, repr(timecode)


def framesToSMPTE(frameRate : int, framesToConvert : int) -> str:
    """
    Takes the given frame rate and number of frames and returns the SMPTE
    timecode string representing that frame count at that frame rate.

    :return The timecode representation as an SMPTE-style string.
    :rtype string
    """
    timecode = Timecode(frameRate, frames=framesToConvert)
    return repr(timecode)


def getDatabasePath() -> str:
    appConfigParser = configparser.ConfigParser()
    appConfigParser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))

    databasePath = pathlib.Path(appConfigParser["ArchiveSettings"]["DATABASE_PATH"])
    
    databasePath.resolve(strict=False).parent.mkdir(parents=True, exist_ok=True)
    databasePath.touch()

    return str(databasePath)


def getExportPath() -> str:
    appConfigParser = configparser.ConfigParser()
    appConfigParser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))

    exportPath = pathlib.Path(appConfigParser["ExportSettings"]["EXPORT_DIRECTORY"])
    
    exportPath.resolve(strict=False).mkdir(parents = True, exist_ok = True)

    return str(exportPath)


def initializeDatabase():
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        try:
            # Create the database if it doesn't already exist
            dbConnection.execute(f"CREATE TABLE IF NOT EXISTS {MAIN_TABLE_NAME} ( \
                {SLATE_DB_COL} TEXT NOT NULL, \
                {TAKE_NUMBER_DB_COL} INT NOT NULL,\
                {CORRECTED_SLATE_DB_COL} TEXT, \
                {CORRECTED_TAKE_DB_COL} INT, \
                {VALID_DB_COL} INT NOT NULL DEFAULT 0, \
                {DATE_DB_COL} TEXT NOT NULL, \
                {FRAME_RATE_DB_COL} INT, \
                {TIMECODE_IN_FRAMES_DB_COL} INT, \
                {TIMECODE_OUT_FRAMES_DB_COL} INT, \
                {TIMECODE_IN_SMPTE_DB_COL} TEXT, \
                {TIMECODE_OUT_SMPTE_DB_COL} TEXT, \
                {LEVEL_SNAPSHOT_DB_COL} TEXT, \
                {LEVEL_SEQUENCE_DB_COL} TEXT, \
                {MAP_DB_COL} TEXT, \
                {USD_ARCHIVE_DB_COL} TEXT, \
                {DESCRIPTION_DB_COL} TEXT, \
                PRIMARY KEY ({SLATE_DB_COL}, {TAKE_NUMBER_DB_COL}) \
                )")

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.initializeDatabase() SQLite Error: {e}")
    
def getMasterSpreadsheetPath() -> str:
    appConfigParser = configparser.ConfigParser()
    appConfigParser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))
    spreadsheetPath = pathlib.Path(appConfigParser["ArchiveSettings"]["MASTER_SPREADSHEET_PATH"])

    return str(spreadsheetPath.resolve(strict=False))


def updateMasterSpreadsheet(slate, take_number):
    take_data = retrieveTake(slate, take_number)
    spreadsheet_writer = SpreadsheetWriter(getMasterSpreadsheetPath())
    spreadsheet_writer.addOrUpdateTake(take_data)


def getBaseArchivePath() -> str:
    appConfigParser = configparser.ConfigParser()
    appConfigParser.read(pathlib.Path(CONFIG_DIR, APP_CONFIG_NAME))
    
    baseArchivePath = pathlib.Path(appConfigParser["ArchiveSettings"]["ARCHIVE_DIRECTORY"])
    return str(baseArchivePath.resolve(strict=False))


def checkTakeExists(slate : str, takeNumber : int) -> bool:
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = { f"{SLATE_DB_COL}" : slate, f"{TAKE_NUMBER_DB_COL}" : takeNumber }

            command = f'SELECT 1 FROM {MAIN_TABLE_NAME} WHERE {SLATE_DB_COL}=:{SLATE_DB_COL} AND {TAKE_NUMBER_DB_COL}=:{TAKE_NUMBER_DB_COL}'
            cursor.execute(command, query)

            if cursor.fetchone():
                return True
            else:
                return False
            
        except sqlite3.OperationalError as e:
             logger.error(f"blackhole.lib.checkRowExists() SQLite Error: {e}")

        finally:
            cursor.close()


def retrieveTake(slate : str, takeNumber : int) -> Take | None:
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = { f"{SLATE_DB_COL}" : slate, f"{TAKE_NUMBER_DB_COL}" : takeNumber }

            command = f'SELECT * FROM {MAIN_TABLE_NAME} WHERE {SLATE_DB_COL}=:{SLATE_DB_COL} AND {TAKE_NUMBER_DB_COL}=:{TAKE_NUMBER_DB_COL}'
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


def retrieveTakes(start_date = None, end_date = None, slate_hint = None) -> list[Take]:
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            command = f'SELECT * FROM {MAIN_TABLE_NAME}'

            query = { 
                START_DATE_FILTER : start_date, 
                END_DATE_FILTER : end_date, 
            }

            # Adding SQL wildcard character to slate hint to indicate it should be
            # treated as the beginning substring of any eligible slate names 
            if slate_hint != None:
                query[SLATE_HINT_FILTER] = slate_hint + '%'

            filterCommands = []

            if start_date != None:
                filterCommands.append(f'{DATE_DB_COL} >= :{START_DATE_FILTER}')

            if end_date != None:
                filterCommands.append(f'{DATE_DB_COL} <= :{END_DATE_FILTER}')

            if slate_hint != None:
                filterCommands.append(f'{SLATE_DB_COL} LIKE :{SLATE_HINT_FILTER}')

            if len(filterCommands) > 0:
                command = command + ' WHERE ' + str.join(' AND ', filterCommands)

            cursor.execute(command, query)

            rawResults = cursor.fetchall()
            results = [Take(**dict(row)) for row in rawResults]

            return results

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.retrieveAllRows() SQLite Error: {e}")
            return []

        finally:
            cursor.close()


def retrieveTakesByList(slateAndTakeList : TakeIDsList, includeCorrections = True) -> list[Take]:
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()
        
        try:
            listAsSqlString = ", ".join([f'("{t[0]}", {t[1]})' for t in slateAndTakeList])

            command = f"SELECT * FROM blackhole_takes WHERE ({SLATE_DB_COL}, {TAKE_NUMBER_DB_COL}) IN ({listAsSqlString})"

            if includeCorrections:
                command += f" OR ({CORRECTED_SLATE_DB_COL}, {CORRECTED_TAKE_DB_COL}) IN ({listAsSqlString})"

            cursor.execute(command)

            rawResults = cursor.fetchall()
            results = [Take(**dict(row)) for row in rawResults]

            return results

        except sqlite3.OperationalError as e:
             logger.error(f"blackhole.lib.retrieveTakesByList() SQLite Error: {e}")

        finally:
            cursor.close() 


def updateTake(take_update : TakeUpdate) -> Take | None:
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = take_update.model_dump(by_alias=True, exclude_none=True)

            updateCommand = f"UPDATE {MAIN_TABLE_NAME} SET "
            setValues = []
            for key in query.keys():
                if key not in (SLATE_DB_COL, TAKE_NUMBER_DB_COL):
                    setValues.append(f"{key} = :{key}")

            if len(setValues) == 0:
                logger.warning("The dictionary given to BlackholeLibrary.updateData() does not contain any values to update. Skipping." )
                return

            updateCommand += ", ".join(setValues)
            updateCommand += f" WHERE {SLATE_DB_COL} = :{SLATE_DB_COL} AND {TAKE_NUMBER_DB_COL} = :{TAKE_NUMBER_DB_COL}"

            cursor.execute(updateCommand, query)
            dbConnection.commit()

            updateMasterSpreadsheet(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])
            return retrieveTake(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])
        
        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.updateRow() SQLite Error: {e}")
            return None

        finally:
            cursor.close()


def insertTake(new_take : TakeCreation) -> Take | None:
    databasePath = getDatabasePath()

    with sqlite3.connect(databasePath) as dbConnection:
        dbConnection.row_factory = sqlite3.Row
        cursor = dbConnection.cursor()

        try:
            query = new_take.model_dump(by_alias=True, exclude_none=True)

            command = f"INSERT INTO {MAIN_TABLE_NAME}"
            placeholderList = []
            for key in query.keys():
                    placeholderList.append(":" + key)

            columns = ", ".join(query.keys())
            placeholders = ", ".join(placeholderList)

            command += f" ({columns}) VALUES ({placeholders})"

            cursor.execute(command, query)
            dbConnection.commit()

            updateMasterSpreadsheet(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])
            return retrieveTake(query[SLATE_DB_COL], query[TAKE_NUMBER_DB_COL])

        except sqlite3.OperationalError as e:
            logger.error(f"blackhole.lib.insertRow() SQLite Error: {e}")
            return None
        
        except sqlite3.IntegrityError as e:
            logger.error(f"blackhole.lib.insertRow() SQLite Error: {e}")
            return None
        
        finally:
            cursor.close()


def copyToExportDirectory(takes : list[Take]) -> tuple[str, list[Take], list[Take]]:
    exportBasePath = pathlib.Path(getExportPath())

    # New export directory is named with a datetime string
    formatString = "%Y-%m-%d_%H-%M-%S"
    nowString = datetime.now().strftime(formatString)

    newExportDirectory = exportBasePath / nowString
    newExportDirectory.mkdir()
    
    # Create a new spreadsheet writer pointed at the new export directory
    exportSpreadsheetPath = pathlib.Path(newExportDirectory, nowString + ".xlsx")
    spreadsheetWriter = SpreadsheetWriter(exportSpreadsheetPath)

    successExports = []
    failedExports = []
    for take in takes:
        if take.usd_export_location:

            # We store the archive paths of our USDs as absolute, but for the 
            # export spreadsheet it's better to switch to relative paths
            usdArchivePath = pathlib.Path(take.usd_export_location)
            archivePathStem = usdArchivePath.relative_to(getBaseArchivePath())

            usdExportPath = newExportDirectory / archivePathStem

            shutil.copytree(usdArchivePath, usdExportPath)
            
            # Write our take data to the export spreadsheet, making sure to update the USD path
            # to the new location
            export_take = take.model_copy(deep=True)
            export_take.usd_export_location = str(pathlib.Path(nowString, archivePathStem))
            spreadsheetWriter.addOrUpdateTake(export_take, createBackup = False)

            successExports.append(export_take)
        else:
            failedExports.append(take)
            logger.warning(f"Take for Slate: {take.slate}, Take Number: {take.take_number} has no USD to export!")
    
    # Create zip file from the new export directory we've made
    zipName = shutil.make_archive(newExportDirectory, 'zip', newExportDirectory)
    
    # Delete the directory now that it's zipped to save space
    shutil.rmtree(newExportDirectory)

    # Return the path to the new zip as a string
    return (zipName, successExports, failedExports)
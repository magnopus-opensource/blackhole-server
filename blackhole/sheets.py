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

from openpyxl import *
from openpyxl.utils.exceptions import SheetTitleException
from blackhole.constants import *
from blackhole.models import *
import pathlib
import shutil
from datetime import date, datetime

class SpreadsheetWriter():
    def __init__(self, workbookPath):
        self.columnMapping = {
            SLATE_DB_COL : 0,
            TAKE_NUMBER_DB_COL : 1,
            CORRECTED_SLATE_DB_COL : 2,
            CORRECTED_TAKE_DB_COL : 3,
            VALID_DB_COL : 4,
            FRAME_RATE_DB_COL : 5,
            TIMECODE_IN_FRAMES_DB_COL : 6,
            TIMECODE_IN_SMPTE_DB_COL : 7,
            TIMECODE_OUT_FRAMES_DB_COL : 8,
            TIMECODE_OUT_SMPTE_DB_COL : 9,
            MAP_DB_COL : 10,
            LEVEL_SEQUENCE_DB_COL : 11,
            LEVEL_SNAPSHOT_DB_COL: 12,
            USD_ARCHIVE_DB_COL : 13,
            DESCRIPTION_DB_COL : 14
        }
        
        self.workbookPath = pathlib.Path(workbookPath)

        if not self.workbookPath.exists():
            self.workbookPath.parent.mkdir(parents = True, exist_ok = True)
            self.workbook = Workbook()
            self.workbook.remove(self.workbook.active)
        else:
            self.workbook = load_workbook(self.workbookPath)

        self._empty = True

    def createOrRetrieveSheet(self, sheetName):
        try:
            sheet = self.workbook[sheetName]  # Attempt to access a nonexistent sheet
            return sheet
        except KeyError:
            sheet = self.workbook.create_sheet(sheetName)

            columnKeys = list(self.columnMapping.keys())
            headerList = [schemaLabelToTitle(key) for key in columnKeys]

            sheet.append(headerList)
            sheet.freeze_panes = "A2"

            self.workbook.save(self.workbookPath)
            self._empty = False
            return sheet

    def createBackup(self):
        if self._empty:
            return

        backupDirPath = self.workbookPath.parent / "Spreadsheet_Backups"
        backupDirPath.mkdir(parents = True, exist_ok = True)

        currentDatetime = datetime.now()
        dateString = currentDatetime.strftime("%Y-%m-%d_%H-%M-%S")
        backupSheetName = self.workbookPath.stem + "_" + dateString + ".xlsx"

        backupWorkbookPath = backupDirPath / backupSheetName

        shutil.copy2(self.workbookPath, backupWorkbookPath)

    def addOrUpdateTake(self, take : Take, createBackup = True):
        if createBackup:
            self.createBackup()

        take_data = take.model_dump(by_alias=True, exclude_none=True)

        # Create new sheet for the data's date if no such sheet exists
        sheet = self.createOrRetrieveSheet(str(take_data[DATE_DB_COL]))

        # Iterate through all non-header rows to see if there's already a row with the slate
        # and take number inside our data
        existingRow = None
        for row in sheet.iter_rows(min_row = 2, max_col = len(self.columnMapping)):
            if row[0].value == take_data[SLATE_DB_COL] and row[1].value == take_data[TAKE_NUMBER_DB_COL]:
                existingRow = row

        if existingRow: # Row exists, update the cells
            for key, value in take_data.items():
                if key in self.columnMapping:
                    row[self.columnMapping[key]].value = value
        else: # Row does not exist, make a new list of elements and append it
            newRow = [take_data.get(key, "") for key in self.columnMapping.keys()]
            sheet.append(newRow)

        self.workbook.save(self.workbookPath)
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

from datetime import date
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from blackhole.recording import RecordingSessionManager
from blackhole.models import *
from blackhole.constants import *
import blackhole.configuration as configs
import blackhole.database_utils as utils

@asynccontextmanager
async def lifespan(app: FastAPI):
    configs.initialize()
    utils.initializeDatabase()
    yield

blackhole_api = FastAPI(title="Blackhole", lifespan=lifespan)
recordingManager = RecordingSessionManager()

@blackhole_api.get('/take/{slate}/{take_number}')
async def get_take(slate : str, take_number : int) -> Take:
    """
    Retrieves a take with the given slate and take number from the database. If no such take exists, returns
    a 404 error.
    """
    retrievedTake = utils.retrieveTake(slate, take_number)

    if retrievedTake:
        return retrievedTake
    else:
        raise HTTPException(status_code=404, detail=f"Take with slate {slate} and take number {take_number} does not exist.")

@blackhole_api.get('/take/')
async def get_takes(start_date : date | None = None, end_date : date | None = None, slate_hint : str | None = None) -> list[Take]:
    """
    Retrieves takes from the database.
    """
    allTakeRows = utils.retrieveTakes(start_date, end_date, slate_hint)

    return allTakeRows

@blackhole_api.put('/take/update')
async def update_take(takeData: Take) -> Take:
    """
    Updates the fields of an existing take in the database. If no take with the given slate and take number
    exists, one will be created with the fields provided in the request body JSON.
    """

    if not utils.checkTakeExists(takeData.slate, takeData.take_number):
        utils.insertTake(takeData)
    else:
        utils.updateTake(takeData)
    
    return takeData


@blackhole_api.get('/recording')
async def get_recording_status():
    """
    Returns Blackhole's current recording status. If the recording status is 'started', the
    slate and take assigned to the recording will also be included in the response.
    """
    isRecording, currentSlate, currentTake = recordingManager.getRecordingStatus()

    if isRecording:
        return { "status" : "started", "slate" : currentSlate, "take_number" : currentTake }
    else:
        return { "status" : "stopped" }


@blackhole_api.post('/recording/{slate}/{take_number}/start')
async def begin_recording(slate : str, take_number : int, frame_rate : int, timecode_in : int, description : str | None = None, map : str | None = None):
    """
    Begins a recording of a take with the given slate and take number. Will return an error if any recording
    is already in progress, or if a take with that slate and take number already exists in the Blackhole database.
    """

    alreadyRecording, currentSlate, currentTake, _ = recordingManager.getRecordingStatus()

    # Can't start a recording if we're already recording, obivously!
    if alreadyRecording:
        return HTTPException(status_code=400, detail=f"Recording already in progress of Slate: {currentSlate}, Take: {currentTake}, request invalid.")
    
    # Check if the slate and take are already in the database so we don't overwrite them
    if utils.checkTakeExists(slate, take_number):
        return HTTPException(status_code=400, detail=f"Slate: {currentSlate}, Take: {currentTake} has already been recorded, request invalid.")
    else:
        current_date = date.today()
        formatted_date = current_date.strftime("%Y-%m-%d")
        
        newTake = TakeCreation(
            slate = slate,
            take_number = take_number,
            date = formatted_date,
            frame_rate = frame_rate,
            timecode_in_frames = timecode_in,
            timecode_in_smpte = utils.framesToSMPTE(frame_rate, timecode_in),
            description = description,
            map = map
        )

        result = utils.insertTake(newTake)

        recordingManager.startRecording(slate, take_number, frame_rate)

        return { "status": "started", "result" : result }


@blackhole_api.post('/recording/{slate}/{take_number}/stop')
async def end_recording(slate : str, take_number : int, timecode_out : int, sequence_path : str | None = None, snapshot_path : str | None = None, description : str | None = None ):
    """
    Ends the recording of a take with the given slate and take number. Will return an error if the slate and take
    don't match that of the recording in progress, or if there is no recording in progress. 
    """
    isRecording, currentSlate, currentTake, currentFrameRate = recordingManager.getRecordingStatus()

    if not isRecording:
        return HTTPException(status_code=400, detail="No recording in progress, request invalid.")
    elif isRecording and (slate != currentSlate or take_number != currentTake):
        return HTTPException(status_code=400, detail=f"Stop recording request was for [Slate: {slate}, Take Number: {take_number}], but current recording is [Slate: {currentSlate}, Take Number: {currentTake}], request invalid.")
    else:
        updatedTake = TakeUpdate(
            slate = slate,
            take_number = take_number,
            timecode_out_frames = timecode_out,
            timecode_out_smpte = utils.framesToSMPTE(currentFrameRate, timecode_out),
            valid = True,
            level_sequence_location = sequence_path,
            level_snapshot_location = snapshot_path,
            description = description
        )

        result = utils.updateTake(updatedTake)
        recordingManager.stopRecording()
        
        return { "status": "stopped", "result" : result }

@blackhole_api.post('/export_selection')
async def export_selected_takes(takes_list : TakeIDsList):
    selectedTakes = utils.retrieveTakesByList(takes_list.id_list)

    (exportLocation, successList, failureList) = utils.copyToExportDirectory(selectedTakes)

    return { 
        "export_location" : exportLocation,
        "successful_exports" : successList,
        "failed_exports" : failureList
    }

@blackhole_api.post('/export_by_date')
async def export_takes_by_date(start_date : date, end_date : date):
    selectedTakes = utils.retrieveTakes(start_date, end_date)

    (exportLocation, successList, failureList) = utils.copyToExportDirectory(selectedTakes)

    return { 
        "export_location" : exportLocation,
        "successful_exports" : successList,
        "failed_exports" : failureList
    }

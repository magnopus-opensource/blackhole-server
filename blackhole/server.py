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

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

import blackhole.configuration as configs
import blackhole.database_utils as utils
from blackhole.models import *
from blackhole.recording import RecordingSessionManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    configs.initialize()
    utils.initialize_database()
    yield


blackhole_api = FastAPI(title="Blackhole", lifespan=lifespan)
recording_manager = RecordingSessionManager()


@blackhole_api.get('/take/{slate}/{take_number}')
async def get_take(slate: str, take_number: int) -> Take:
    """
    Retrieves a take with the given slate and take number from the database. If no such take exists, returns
    a 404 error.
    """
    retrieved_take = utils.retrieve_take(slate, take_number)

    if retrieved_take:
        return retrieved_take
    else:
        raise HTTPException(status_code=404,
                            detail=f"Take with slate {slate} and take number {take_number} does not exist.")


@blackhole_api.get('/take/')
async def get_takes(start_date: date | None = None, end_date: date | None = None, slate_hint: str | None = None) \
                    -> list[Take]:
    """
    Retrieves takes from the database.
    """
    all_take_rows = utils.retrieve_takes(start_date, end_date, slate_hint)

    return all_take_rows


@blackhole_api.put('/take/update')
async def update_take(take_data: TakeUpdate) -> Take:
    """
    Updates the fields of an existing take in the database. If no take with the given slate and take number
    exists, one will be created with the fields provided in the request body JSON.
    """
    if not utils.check_take_exists(take_data.slate, take_data.take_number):
        return utils.insert_take(take_data)
    else:
        return utils.update_take(take_data)


@blackhole_api.get('/recording')
async def get_recording_status():
    """
    Returns Blackhole's current recording status. If the recording status is 'started', the
    slate and take assigned to the recording will also be included in the response.
    """
    is_recording, current_slate, current_take = recording_manager.get_recording_status()

    if is_recording:
        return {"status": "started", "slate": current_slate, "take_number": current_take}
    else:
        return {"status": "stopped"}


@blackhole_api.post('/recording/{slate}/{take_number}/start')
async def begin_recording(slate: str, take_number: int, frame_rate: int, timecode_in: int,
                          description: str | None = None, map_name: str | None = None):
    """
    Begins a recording of a take with the given slate and take number. Will return an error if any recording
    is already in progress, or if a take with that slate and take number already exists in the Blackhole database.
    """

    already_recording, current_slate, current_take, _ = recording_manager.get_recording_status()

    # Can't start a recording if we're already recording, obivously!
    if already_recording:
        return HTTPException(status_code=400,
                             detail=f"Recording already in progress of Slate: {current_slate}, "
                                    f"Take: {current_take}, request invalid.")

    # Check if the slate and take are already in the database so that we don't overwrite them
    if utils.check_take_exists(slate, take_number):
        return HTTPException(status_code=400,
                             detail=f"Slate: {current_slate}, Take: {current_take} has already been recorded, "
                                    f"request invalid.")
    else:
        current_date = date.today()
        formatted_date = current_date.strftime("%Y-%m-%d")

        new_take = TakeCreation(
            slate=slate,
            take_number=take_number,
            date=formatted_date,
            frame_rate=frame_rate,
            timecode_in_frames=timecode_in,
            timecode_in_smpte=utils.frames_to_smpte(frame_rate, timecode_in),
            description=description,
            map=map_name
        )

        result = utils.insert_take(new_take)

        recording_manager.start_recording(slate, take_number, frame_rate)

        return {"status": "started", "result": result}


@blackhole_api.post('/recording/{slate}/{take_number}/stop')
async def end_recording(slate: str, take_number: int, timecode_out: int, sequence_path: str | None = None,
                        snapshot_path: str | None = None, description: str | None = None):
    """
    Ends the recording of a take with the given slate and take number. Will return an error if the slate and take
    don't match that of the recording in progress, or if there is no recording in progress. 
    """
    is_recording, current_slate, current_take, current_frame_rate = recording_manager.get_recording_status()

    if not is_recording:
        return HTTPException(status_code=400, detail="No recording in progress, request invalid.")
    elif is_recording and (slate != current_slate or take_number != current_take):
        return HTTPException(status_code=400,
                             detail=f"Stop recording request was for [Slate: {slate}, Take Number: {take_number}], "
                                    f"but current recording is [Slate: {current_slate}, Take Number: {current_take}], "
                                    f"request invalid.")
    else:
        updated_take = TakeUpdate(
            slate=slate,
            take_number=take_number,
            timecode_out_frames=timecode_out,
            timecode_out_smpte=utils.frames_to_smpte(current_frame_rate, timecode_out),
            valid=True,
            level_sequence_location=sequence_path,
            level_snapshot_location=snapshot_path,
            description=description
        )

        result = utils.update_take(updated_take)
        recording_manager.stop_recording()

        return {"status": "stopped", "result": result}


@blackhole_api.post('/export_selection')
async def export_selected_takes(takes_list: TakeIDsList):
    selected_takes = utils.retrieve_takes_by_list(takes_list)

    (exportLocation, successList, failureList) = utils.copy_to_export_directory(selected_takes)

    return {
        "export_location": exportLocation,
        "successful_exports": successList,
        "failed_exports": failureList
    }


@blackhole_api.post('/export_by_date')
async def export_takes_by_date(start_date: date, end_date: date):
    selected_takes = utils.retrieve_takes(start_date, end_date)

    (exportLocation, successList, failureList) = utils.copy_to_export_directory(selected_takes)

    return {
        "export_location": exportLocation,
        "successful_exports": successList,
        "failed_exports": failureList
    }

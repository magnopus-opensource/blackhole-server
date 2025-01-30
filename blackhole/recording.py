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
import importlib
import logging
import pathlib
import socket
from threading import Thread, Event

import blackhole.database_utils as utils
from blackhole.models import *
from blackhole.usd_export import UsdArchiver, USDMasterStageArchiver

logger = logging.getLogger(__name__)


class Recording(Thread):
    def __init__(self, slate, take_number, frame_rate, stop_event, stop_callback):
        super().__init__()
        self.slate = slate
        self.take_number = take_number
        self.frame_rate = frame_rate
        self._stop_event = stop_event
        self._stopped_capture_callback = stop_callback

        self._device_config = configparser.ConfigParser()
        self._device_config.read("blackhole_config/device_config.ini")

        self.archive_path = pathlib.Path(utils.get_base_archive_path(), self.slate, str(self.take_number))

    def run(self):
        device_capture_data = self.start_capturing_data()

        # Tell the RecordingSessionManager we are no longer capturing, so it's free to start another recording
        self._stopped_capture_callback()

        # Turn our capture data into USDs
        self.archive_captured_data(device_capture_data)

        # Record the location of the USDs in the database and the master spreadsheet
        self.update_database_with_archive_path()

        logger.info(f"USD archive for Slate: {self.slate}, Take: {self.take_number} complete!")

    def start_capturing_data(self):
        capture_threads = []
        devices = set()

        for device_name in self._device_config.sections():
            # Only allow recording to start if all device names are unique
            if device_name in devices:
                raise ValueError(f"Duplicate device name found in configs: {device_name}. ")
            thread_devices.add(device_name)

            try:
                discovered_port = int(self._device_config[device_name]["PORT"])
                protocol = self._device_config[device_name]["TRACKING_PROTOCOL"]
            except KeyError as e:
                logger.error(f"Can't find key {e}, skipping. \n-----> Please add {e} to "
                             f"blackhole_config/device_config.ini under the section labled {device_name}")
                continue

            try:
                capture_module = importlib.import_module(f"blackhole.device_capture.{protocol.lower()}_capture")
                capture_thread_class = getattr(capture_module, "{0}CaptureThread".format(protocol))
                capture_thread_instance = capture_thread_class(self.frame_rate, device_name, discovered_port,
                                                               self._stop_event)

                capture_threads.append(capture_thread_instance)
            except socket.gaierror:
                logger.error(f"Tracking thread for device '{device_name}' can't bind socket to Port={discovered_port}."
                             "\n-----> Please check that blackhole_config/device_config.ini has the correct port "
                             "assigned for the device, and that another socket is not already listening on that port.")
                continue

        for thread in capture_threads:
            logger.info(f"Beginning capture of {thread.device_name} for Slate: {self.slate}, Take: {self.take_number}")
            thread.start()

        # The threads will stop once the stopEvent we gave them is set by the RecordingSessionManager
        device_capture_data = {}
        for thread in capture_threads:
            thread.join()

            for device_name, values in thread.data_to_export:
                device_capture_data[device_name] = values

        return device_capture_data

    def archive_captured_data(self, device_capture_dict):
        # Get db sequence row:
        take = utils.retrieve_take(self.slate, self.take_number)

        if take:
            sub_usd_threads = []
            for device_name, capture_data in device_capture_dict.items():
                sub_archive_path = pathlib.Path(self.archive_path, "cameras", device_name, f'{device_name}.usda')
                archiver = UsdArchiver(
                    sub_archive_path,
                    take.slate,
                    take.take_number,
                    take.frame_rate,
                    take.timecode_in_frames,
                    take.timecode_out_frames,
                    take.map,
                    capture_data
                )
                sub_usd_threads.append(archiver)

            # Start each of our child USD renders, then wait for them to finish
            for thread in sub_usd_threads:
                logger.info(f"Beginning render of subsequence to {thread.sub_archive_path}")
                thread.start()

            for thread in sub_usd_threads:
                thread.join()

            # The master USD file will reference each of the capture data USDs via a relative path
            device_archive_relative_paths = [subThread.sub_archive_path.relative_to(self.archive_path) for subThread
                                             in sub_usd_threads]
            master_archive_path = pathlib.Path(self.archive_path, "master", 'MasterSequence.usda')
            master_archive_thread = USDMasterStageArchiver(master_archive_path, device_archive_relative_paths)

            logger.info(f"Beginning render of master sequence to {master_archive_thread.archivePath}")
            master_archive_thread.start()
            master_archive_thread.join()
        else:
            logger.error(f"Can't archive recorded data to USD. No data for Slate: {self.slate}, "
                         f"Take {self.take_number} was recorded to the database.")

    def update_database_with_archive_path(self):
        take = utils.retrieve_take(self.slate, self.take_number)
        take_update = TakeUpdate(**take.model_dump(by_alias=True, exclude_none=True))
        take_update.usd_export_location = str(self.archive_path)
        utils.update_take(take_update)


class RecordingSessionManager:
    def __init__(self):
        self._current_recording: Recording | None = None
        self._stop_recording_event = Event()

    def get_recording_status(self):
        if self._current_recording is None:
            return False, None, None, None
        else:
            return (True, self._current_recording.slate, self._current_recording.take_number,
                    self._current_recording.frame_rate)

    def reset_recording_state(self):
        self._stop_recording_event.clear()
        self._current_recording = None

    def start_recording(self, slate, take_number, frame_rate):
        is_recording, _, _, _ = self.get_recording_status()

        if is_recording:
            return

        self._current_recording = Recording(slate, take_number, frame_rate, self._stop_recording_event,
                                            self.reset_recording_state)
        self._current_recording.start()

    def stop_recording(self):
        is_recording, _, _, _ = self.get_recording_status()

        if is_recording:
            self._stop_recording_event.set()

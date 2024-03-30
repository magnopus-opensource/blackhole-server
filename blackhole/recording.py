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
import socket
import importlib
import logging
import blackhole.database_utils as utils
from threading import Thread, Event, Lock
from typing import Callable
from blackhole.usd_export import UsdArchiver, USDMasterStageArchiver
from blackhole.constants import *
from blackhole.models import *

logger = logging.getLogger(__name__)

class Recording(Thread):
    def __init__(self, slate, takeNumber, frameRate, stopEvent, stopCallback):
        super().__init__()
        self.slate = slate
        self.takeNumber = takeNumber
        self.frameRate = frameRate
        self._stopEvent = stopEvent
        self._stoppedCaptureCallback = stopCallback

        self._deviceConfig = configparser.ConfigParser()
        self._deviceConfig.read("blackhole_config/device_config.ini")

        self.archivePath = pathlib.Path(utils.getBaseArchivePath(), self.slate, str(self.takeNumber))

    def run(self):
        deviceCaptureData = self.startCapturingData()

        # Tell the RecordingSessionManager we are no longer capturing, so it's free to start another recording
        self._stoppedCaptureCallback()

        # Turn our capture data into USDs
        self.archiveCapturedData(deviceCaptureData)

        # Record the location of the USDs in the database and the master spreadsheet
        self.updateDatabaseWithArchivePath()
        
        logger.info(f"USD archive for Slate: {self.slate}, Take: {self.takeNumber} complete!")     

    def startCapturingData(self):
        captureThreads = []

        for deviceName in self._deviceConfig.sections():
            try:
                discoveredIP = self._deviceConfig[deviceName]["IP_ADDRESS"]
                discoveredPort = int(self._deviceConfig[deviceName]["PORT"])
                protocol = self._deviceConfig[deviceName]["TRACKING_PROTOCOL"]

                captureThreadSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                captureThreadSocket.bind(("", discoveredPort))

                captureModule = importlib.import_module(f"blackhole.device_capture.{protocol.lower()}_capture")
                captureThreadClass = getattr(captureModule, "{0}CaptureThread".format(protocol))
                captureThreadInstance = captureThreadClass(self.frameRate, deviceName, captureThreadSocket, self._stopEvent)
                
                captureThreads.append(captureThreadInstance)
            
            except KeyError as e:
                logger.error("Can't find key {0}, skipping. \n-----> Please add {0} to config/deviceConfig.ini under the section labled {1}".format(e, deviceName))
                continue
            except socket.gaierror:
                logger.error(f"Tracking device '{deviceName}' cannot resolve with IP={discoveredIP}, Port={discoveredPort}. Please check config/deviceConfig.ini.")
                captureThreadSocket.close()
                continue
        
        for thread in captureThreads:
            logger.info(f"Beginning capture of {thread.deviceName} for Slate: {self.slate}, Take: {self.takeNumber}")
            thread.start()

        # The threads will stop once the stopEvent we gave them is set by the RecordingSessionManager
        deviceCaptureData = {}
        for thread in captureThreads:
            thread.join()
            deviceCaptureData[thread.deviceName] = thread.dataToExport

        return deviceCaptureData

    def archiveCapturedData(self, deviceCaptureDict):
        # Get db sequence row:
        take = utils.retrieveTake(self.slate, self.takeNumber)

        if take:
            subUsdThreads = []
            for deviceName, captureData in deviceCaptureDict.items():
                subArchivePath = pathlib.Path(self.archivePath, "cameras", deviceName, f'{deviceName}.usda')
                archiver = UsdArchiver(
                                subArchivePath, 
                                take.slate, 
                                take.take_number, 
                                take.frame_rate, 
                                take.timecode_in_frames, 
                                take.timecode_out_frames, 
                                take.map, 
                                captureData
                            )
                subUsdThreads.append(archiver)

            # Start each of our child USD renders, then wait for them to finish
            for thread in subUsdThreads:
                logger.info(f"Beginning render of {deviceName} subsequence to {thread.archivePath}")
                thread.start()

            for thread in subUsdThreads:
                thread.join()

            # The master USD file will reference each of the capture data USDs via a relative path
            deviceArchiveRelativePaths = [ subThread.archivePath.relative_to(self.archivePath) for subThread in subUsdThreads ]
            masterArchivePath = pathlib.Path(self.archivePath, "master", 'MasterSequence.usda')
            masterArchiveThread = USDMasterStageArchiver(masterArchivePath, deviceArchiveRelativePaths)

            logger.info(f"Beginning render of master sequence to {masterArchiveThread.archivePath}")        
            masterArchiveThread.start()
            masterArchiveThread.join()
        else:
            logger.error(f"Can't archive recorded data to USD. No data for Slate: {self.slate}, Take {self.takeNumber} was recorded to the database.")

    def updateDatabaseWithArchivePath(self):
        take = utils.retrieveTake(self.slate, self.takeNumber)
        take_update = TakeUpdate(**take.model_dump(by_alias=True, exclude_none=True))
        take_update.usd_export_location = str(self.archivePath)
        utils.updateTake(take_update)


class RecordingSessionManager():
    def __init__(self):
        self._currentRecording : Recording = None
        self._stopRecordingEvent = Event()

    def getRecordingStatus(self):
        if self._currentRecording == None:
            return (False, None, None, None)
        else:
            return (True, self._currentRecording.slate, self._currentRecording.takeNumber, self._currentRecording.frameRate)

    def resetRecordingState(self):
        self._stopRecordingEvent.clear()
        self._currentRecording = None

    def startRecording(self, slate, takeNumber, frameRate):
        isRecording, _, _, _ = self.getRecordingStatus()

        if isRecording:
            return

        self._currentRecording = Recording(slate, takeNumber, frameRate, self._stopRecordingEvent, self.resetRecordingState)
        self._currentRecording.start()

    def stopRecording(self):
        isRecording, _, _, _ = self.getRecordingStatus()

        if isRecording:
            self._stopRecordingEvent.set()

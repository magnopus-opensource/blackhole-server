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

from abc import ABC, abstractmethod
from threading import Thread, Event
import select
import socket

class BaseCaptureThread(Thread, ABC):
    def __init__(self, frameRate : int, deviceName : str, socket : socket, stopEvent : Event):
        super().__init__()
        self.listeningSocket = socket
        
        self.deviceName = deviceName
        self.frameRate = frameRate

        self.capturedTrackingData = [] 
        self.dataToExport = None

        self.stopEvent = stopEvent

    @property
    @abstractmethod
    def packet_size(self):
        """
        Property expressing the size of packets sent over the network by the hardware. Must be
        defined by subclasses.
        """
        pass

    @abstractmethod
    def parsePacket(self, packetBytes):
        """
        Used to process the raw bytes of a packet sent by your device into an object containing
        the transform information of a frame. Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def validateParsedData(self, parsedPacket):
        """
        Used to validate the results of a call to parsePacket. Must be implemented by
        subclasses.
        """
        pass
    
    def cacheParsedData(self, parsedPacket):
        """
        Used to append parsed frame data to the list of data collected so far. This should take the
        form of a dictionary with key-value pairs for X,Y,Z position and rotation, and the timecode
        as frames (see BlackholeConstants for what keys to use).
        """
        self.capturedTrackingData.append(parsedPacket)

    def cleanup(self):
        """
        Used to clean up any remaining resources being used by the thread after capture has stopped.
        """
        self.listeningSocket.shutdown(socket.SHUT_RDWR)
        self.listeningSocket.close()

    def run(self):
        try:
            while not self.stopEvent.is_set():
                ready, _, _ = select.select([self.listeningSocket], [], [], 1)
                
                for sock in ready:
                    packet = sock.recv(self.packet_size)

                    trackingData = self.parsePacket(packet)
                    
                    if self.validateParsedData(trackingData):
                        self.cacheParsedData(trackingData)

        except Exception as e:
            print(e)
        
        finally:
            self.dataToExport = list(self.capturedTrackingData)
            self.cleanup()

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

import logging
import select
import socket
from abc import ABC, abstractmethod
from threading import Thread, Event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BaseCaptureThread(Thread, ABC):
    def __init__(self, frame_rate: int, device_name: str, port: int, stop_event: Event):
        super().__init__()

        self.device_name = device_name
        self.frame_rate = frame_rate

        self.captured_tracking_data = []
        self.data_to_export = None

        self.stop_event = stop_event

        try:
            self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listening_socket.bind(("", port))

        except socket.gaierror as e:
            raise ConnectionError(f"Failed to resolve capture thread UDP connection on port {port}") from e

    @property
    @abstractmethod
    def packet_size(self):
        """
        Property expressing the size of packets sent over the network by the hardware. Must be
        defined by subclasses.
        """
        pass

    @abstractmethod
    def parse_packet(self, packet_bytes):
        """
        Used to process the raw bytes of a packet sent by your device into an object containing
        the transform information of a frame. Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def validate_parsed_data(self, parsed_packet):
        """
        Used to validate the results of a call to parsePacket. Must be implemented by
        subclasses.
        """
        pass

    def cache_parsed_data(self, parsed_packet):
        """
        Used to append parsed frame data to the list of data collected so far. This should take the
        form of a dictionary with key-value pairs for X,Y,Z position and rotation, and the timecode
        as frames (see BlackholeConstants for what keys to use).
        """
        self.captured_tracking_data.append(parsed_packet)

    def cleanup(self):
        """
        Used to clean up any remaining resources being used by the thread after capture has stopped.
        """
        self.listening_socket.shutdown(socket.SHUT_RDWR)
        self.listening_socket.close()

    def run(self):
        try:
            while not self.stop_event.is_set():
                ready, _, _ = select.select([self.listening_socket], [], [], 1)

                for sock in ready:
                    packet = sock.recv(self.packet_size)

                    tracking_data = self.parse_packet(packet)

                    if self.validate_parsed_data(tracking_data):
                        self.cache_parsed_data(tracking_data)

        except Exception as e:
            print(e)

        finally:
            self.data_to_export = list(self.captured_tracking_data)
            self.cleanup()

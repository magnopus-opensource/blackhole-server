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

from .base_capture import BaseCaptureThread, logger
from blackhole.constants import *
import blackhole.database_utils as utils
import struct

PACKET_FORMAT = '!cc3s3s3s3s3s3s3s3s2sc'  # All FreeD position/orientation data is sent in 29-byte packets.
FREED_PACKET_SIZE = struct.calcsize(PACKET_FORMAT)


class FreeDPacket:
    def __init__(self, packet_data: bytes):
        if len(packet_data) != FREED_PACKET_SIZE:
            logger.error(f"FreeD camera transform packet must contain {FREED_PACKET_SIZE} bytes.")
            return

        self.packetBytes = packet_data

        (message_type_byte,
         camera_id_byte,
         pan_bytes,
         tilt_bytes,
         roll_bytes,
         x_bytes,
         y_bytes,
         z_bytes,
         zoom_byte,
         focus_byte,
         spare_bytes,
         checksum_byte) = struct.unpack(PACKET_FORMAT, self.packetBytes)

        self.cam_id = int.from_bytes(camera_id_byte, byteorder='big')

        # All rotation values are expressed in degrees ranging from -180 t0 180
        self.rot_pan = self.get_freed_float(pan_bytes, 15)
        self.rot_tilt = self.get_freed_float(tilt_bytes, 15)
        self.rot_roll = self.get_freed_float(roll_bytes, 15)

        # All position values are expressed in millimeters
        self.pos_x = self.get_freed_float(x_bytes, 6)
        self.pos_y = self.get_freed_float(y_bytes, 6)
        self.pos_z = self.get_freed_float(z_bytes, 6)

        # Zoom and focus are unsigned values of arbitrary units to be
        # interpreted by whatever system you use
        self.zoom = int.from_bytes(zoom_byte, byteorder='big')
        self.focus = int.from_bytes(focus_byte, byteorder='big')

        self.spare = int.from_bytes(spare_bytes, byteorder='big')
        self.checksum = int.from_bytes(checksum_byte, byteorder='big')

    def __str__(self):
        return (f"CAMERA ID: {self.cam_id} \n"
                f"PAN: {self.rot_pan} \n"
                f"TILT: {self.rot_tilt} \n"
                f"ROLL: {self.rot_roll} \n"
                f"POSITION: ({self.pos_x},{self.pos_y},{self.pos_z}) \n"
                f"ZOOM: {self.zoom} \n"
                f"FOCUS: {self.focus} \n"
                f"CHECKSUM: {hex(self.checksum)} \n"
                f"CHECKSUM VALID: {self.checksum_valid()} \n")

    def get_freed_float(self, raw_bytes: bytes, fractional_byte_size: int):
        non_fractional = int.from_bytes(raw_bytes, byteorder='big', signed=True)
        fractional = non_fractional / float(1 << fractional_byte_size)

        return fractional

    def checksum_valid(self):
        """
        The checksum of FreeD packets is calculated by subtracting (mod 256)
        each byte of the packet from 0x40. Including the checksum byte itself
        in this calculation should result in a value of 0 if the packet is valid.
        """

        sum_remaining = 0x40

        for byte in self.packetBytes:
            sum_remaining = (sum_remaining - byte) & 0xFF  # Take mod 256 each time

        return sum_remaining == 0


class FreeDCaptureThread(BaseCaptureThread):
    @property
    def packet_size(self):
        return FREED_PACKET_SIZE

    def package_frame_data(self, packet: FreeDPacket):
        data = dict()

        # Convert the camera transform from FreeD's conventions to USD.
        #
        # The FreeD protocol uses a right-handed coordinate space with +Z up, +Y forward, +X right. Positions are 
        # measured in millimeters.
        # 
        # USD also uses a right-handed coordinate space, but with +Y as up, -Z as forward, and +X as right (unless
        # configured otherwise). Positions are measured in centimeters (unless configured otherwise).
        #
        # FreeD departs from right-handed coordinate system conventions by having positive pan direction be clockwise
        # rather than counterclockwise.
        #
        # Unreal FRotators actually use the same positive rotation direction conventions as FreeD, so in a direct
        # conversion between the two the only change to the transform would be swapping the X and Y axes.
        #
        # When Unreal converts USD cameras it subtracts a 90 degree yaw rotation because USD cameras use -Z as their
        # local forward while Unreal cameras use +X. So, we add a 90 degree yaw rotation to the FreeD rotation to
        # compensate for this.
        #
        # In a scenario where we’ve recorded a camera’s motion into a level sequence in Unreal while simultaneously
        # recording a USD of that same camera in Blackhole, this step will ensure that when we import the USD camera
        # track into Unreal, it matches the orientation of the camera track in the level sequence.
        #
        # Note that tilt, pan, and roll are equivalent to pitch, yaw, and roll, respectively.
        #
        # References:
        # - https://www.manualsdir.com/manuals/641433/vinten-radamec-free-d.html?page=40
        # - Unreal Engine USDImporter plugin code, USDPrimConversion.cpp, function UsdToUnreal::ConvertXformable(),
        #   lines 329-386
        data[TRACKING_X] = packet.pos_y / 10.0
        data[TRACKING_Y] = packet.pos_z / 10.0
        data[TRACKING_Z] = packet.pos_x / 10.0

        data[TRACKING_PITCH] = packet.rot_tilt
        data[TRACKING_YAW] = -(packet.rot_pan + 90)
        data[TRACKING_ROLL] = packet.rot_roll

        data[TRACKING_TIMECODE_KEY] = utils.get_system_timecode_as_frames(self.frame_rate)

        return data

    def parse_packet(self, packet_bytes):
        if packet_bytes[0:1] == b"\xd1":
            transform_packet_object = FreeDPacket(packet_bytes)
            logger.info(transform_packet_object)

            return transform_packet_object
        else:
            return None

    def validate_parsed_data(self, parsed_packet):
        if parsed_packet is None or not isinstance(parsed_packet, FreeDPacket):
            return False
        else:
            return parsed_packet.checksum_valid()

    def cache_parsed_data(self, parsed_packet):
        transform_data = self.package_frame_data(parsed_packet)
        self.captured_tracking_data.append(transform_data)

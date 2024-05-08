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
import pathlib
from threading import Thread

from pxr import Kind, Sdf, Usd, UsdGeom, Gf

from blackhole.constants import *

logger = logging.getLogger(__name__)


class UsdArchiver(Thread):
    def __init__(self, sub_archive_path, slate, take_number, frame_rate, timecode_in, timecode_out, map_name,
                 captured_transform_data):
        super().__init__()
        self.sub_archive_path = sub_archive_path
        self.filename = pathlib.Path(sub_archive_path).stem
        self.slate = slate
        self.take_number = take_number
        self.timecode_in = timecode_in
        self.timecode_out = timecode_out
        self.frame_rate = frame_rate
        self.map = map_name
        self.captured_transform_data = captured_transform_data

    def run(self):
        stage = Usd.Stage.CreateNew(str(self.sub_archive_path))
        stage.SetStartTimeCode(self.timecode_in)
        stage.SetEndTimeCode(self.timecode_out)
        stage.SetFramesPerSecond(self.frame_rate)

        anim_xform = UsdGeom.Xform.Define(stage, '/World/anim')

        Usd.ModelAPI(UsdGeom.Xform.Define(stage, '/World')).SetKind(Kind.Tokens.group)
        Usd.ModelAPI(UsdGeom.Xform.Define(stage, '/World/anim')).SetKind(Kind.Tokens.group)

        camera_prim = UsdGeom.Camera.Define(stage, '/World/anim/' + self.filename)
        Usd.ModelAPI(camera_prim).SetKind(Kind.Tokens.group)

        # cubePrim = UsdGeom.Cube.Define(stage, '/World/anim/refCube')

        xform_api = UsdGeom.Xformable(camera_prim)
        translate_op = xform_api.AddTranslateOp()
        rotate_op = xform_api.AddRotateXYZOp()

        self.add_attributes(stage)

        for captureDict in self.captured_transform_data:
            x = captureDict[TRACKING_X]
            y = captureDict[TRACKING_Y]
            z = captureDict[TRACKING_Z]

            pitch = captureDict[TRACKING_PITCH]
            yaw = captureDict[TRACKING_YAW]
            roll = captureDict[TRACKING_ROLL]

            translation_vector = Gf.Vec3d((float(x), float(y), float(z)))
            rotation_vector = Gf.Vec3d((float(pitch), float(yaw), float(roll)))

            frame = captureDict[TRACKING_TIMECODE_KEY]

            translate_op.Set(translation_vector, frame)
            rotate_op.Set(rotation_vector, frame)

        stage.GetRootLayer().Save()

    def add_attributes(self, stage):
        # Define Slate and Take as the metadata of the anim prim
        slate_attribute = stage.GetPrimAtPath("/World/anim").CreateAttribute("Slate", Sdf.ValueTypeNames.String)
        slate_attribute.Set(self.slate)

        take_number_attribute = stage.GetPrimAtPath("/World/anim").CreateAttribute("TakeNumber", Sdf.ValueTypeNames.Int)
        take_number_attribute.Set(self.take_number)

        if self.map is not None:
            # Define the Map as the metadata of the World prim
            map_attribute = stage.GetPrimAtPath("/World").CreateAttribute("Map", Sdf.ValueTypeNames.String)
            map_attribute.Set(self.map)


class USDMasterStageArchiver(Thread):
    def __init__(self, archive_path, files_to_append):
        super().__init__()
        self.archivePath = archive_path
        self.filesToAppend = files_to_append

    def run(self):
        logger.info(f"Creating new stage on {self.archivePath}")
        stage = Usd.Stage.CreateNew(str(self.archivePath))

        for filePath in self.filesToAppend:
            path_with_forward_slashes = filePath.as_posix()

            stage.GetRootLayer().subLayerPaths.append("../" + path_with_forward_slashes)
            logger.info(f"Adding sublayer to master USD: {path_with_forward_slashes}")

        stage.GetRootLayer().Save()

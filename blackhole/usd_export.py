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
import logging
from blackhole.constants import *
from threading import Thread
from pxr import Kind, Sdf, Usd, UsdGeom, Gf

logger = logging.getLogger(__name__)

class UsdArchiver(Thread):
    def __init__(self, archivePath, slate, takeNumber, frameRate, timecodeIn, timecodeOut, map, capturedTransformData):
        super().__init__()
        self.archivePath = archivePath
        self.filename = pathlib.Path(archivePath).stem
        self.slate = slate
        self.takeNumber = takeNumber
        self.timecodeIn = timecodeIn
        self.timecodeOut = timecodeOut
        self.frameRate = frameRate
        self.map = map
        self.capturedTransformData = capturedTransformData

    def run(self):
        stage = Usd.Stage.CreateNew(str(self.archivePath))
        stage.SetStartTimeCode(self.timecodeIn)
        stage.SetEndTimeCode(self.timecodeOut)
        stage.SetFramesPerSecond(self.frameRate)

        animXform = UsdGeom.Xform.Define(stage, '/World/anim')

        Usd.ModelAPI(UsdGeom.Xform.Define(stage, '/World')).SetKind(Kind.Tokens.group)
        Usd.ModelAPI(UsdGeom.Xform.Define(stage, '/World/anim')).SetKind(Kind.Tokens.group)

        cameraPrim = UsdGeom.Camera.Define(stage, '/World/anim/' + self.filename)
        Usd.ModelAPI(cameraPrim).SetKind(Kind.Tokens.group)

        #cubePrim = UsdGeom.Cube.Define(stage, '/World/anim/refCube')

        xformAPI = UsdGeom.Xformable(cameraPrim)
        translateOp = xformAPI.AddTranslateOp()
        rotateOp = xformAPI.AddRotateXYZOp()

        self.addAttributes(stage)

        for captureDict in self.capturedTransformData:
            x = captureDict[TRACKING_X]
            y = captureDict[TRACKING_Y]
            z = captureDict[TRACKING_Z]

            pitch = captureDict[TRACKING_PITCH]
            yaw = captureDict[TRACKING_YAW]
            roll = captureDict[TRACKING_ROLL]

            translationVector = Gf.Vec3d((float(x), float(y), float(z)))
            rotationVector = Gf.Vec3d((float(pitch), float(yaw), float(roll)))

            frame = captureDict[TRACKING_TIMECODE_KEY]

            translateOp.Set((translationVector), frame)
            rotateOp.Set((rotationVector), frame)

        stage.GetRootLayer().Save()

    def addAttributes(self, stage):
        # Define Slate and Take as the metadata of the anim prim
        slate_attribute = stage.GetPrimAtPath("/World/anim").CreateAttribute("Slate", Sdf.ValueTypeNames.String)
        slate_attribute.Set(self.slate)

        take_number_attribute = stage.GetPrimAtPath("/World/anim").CreateAttribute("TakeNumber", Sdf.ValueTypeNames.Int)
        take_number_attribute.Set(self.takeNumber)

        if self.map is not None:
            # Define the Map as the metadata of the World prim
            map_attribute = stage.GetPrimAtPath("/World").CreateAttribute("Map", Sdf.ValueTypeNames.String)
            map_attribute.Set(self.map)
            
        
class USDMasterStageArchiver(Thread):
    def __init__(self, archivePath, filesToAppend):
        super().__init__()
        self.archivePath = archivePath
        self.filesToAppend = filesToAppend
    
    def run(self):  
        logger.info(f"Creating new stage on {self.archivePath}")
        stage = Usd.Stage.CreateNew(str(self.archivePath))
        
        for filePath in self.filesToAppend:
            pathWithForwardSlashes = filePath.as_posix()

            stage.GetRootLayer().subLayerPaths.append("../"+ pathWithForwardSlashes)
            logger.info(f"Adding sublayer to master USD: {pathWithForwardSlashes}")
        
        stage.GetRootLayer().Save()
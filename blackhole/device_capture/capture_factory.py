from typing import Any
import importlib
import socket
import logging

from .base_capture import BaseCaptureThread, SingleDeviceCaptureThread, MultiDeviceCaptureThread
from .freed_capture import FreeDCaptureThread

logger = logging.getLogger(__name__)

class CaptureThreadFactory:
    @staticmethod
    def create_capture_threads(device_configs: dict[str, dict[str,str]], frame_rate: int, stop_event):
        """
        Creates capture threads based on device configurations.
        Handles grouping of devices that share ports.
        
        Args:
            device_configs: Dictionary of device configurations from config file
            frame_rate: Frame rate to capture at
            stop_event: Event to signal thread stop
        """
        assigned_ports: dict[str, BaseCaptureThread] = {}
        devices_to_capture: list[str] = []

        for device_name, config in device_configs.items():
            port = int(config["PORT"])
            protocol = config["TRACKING_PROTOCOL"]

            # Device names should be unique
            if device_name in devices_to_capture:
                raise ValueError(f"Duplicate device name found in configs: {device_name}. ")
            else:
                devices_to_capture.append(device_name)

            if port in assigned_ports:
                assigned_thread = assigned_ports[port]
                assigned_protocol = assigned_thread.protocol

                if not issubclass(assigned_thread, MultiDeviceCaptureThread):
                    logger.error("Port %s conflict: Can't add %s with protocol %s when the port is already assigned a single-device capture thread.", port, device_name, protocol)
                    continue
                elif protocol != assigned_protocol:
                    logger.error("Port %s conflict: Can't add %s with protocol %s as the port's capture thread uses protocol %s.", port, device_name, protocol, assigned_protocol)
                    continue
                else:
                    assigned_thread.add_device(device_name, config)
            else:
                try:
                    capture_module = importlib.import_module(f"blackhole.device_capture.{protocol.lower()}_capture")
                    capture_thread_class = getattr(capture_module, f"{protocol}CaptureThread")

                    if issubclass(capture_thread_class, MultiDeviceCaptureThread):
                        capture_thread_instance = capture_thread_class(frame_rate, port, stop_event, { device_name : config })
                    else:
                        # First step is just making sure that things will still work when we force use of the original 
                        # FreeDCaptureThread implementation.
                        capture_thread_instance = FreeDCaptureThread(frame_rate, device_name, port, stop_event)
                        # capture_thread_instance = capture_thread_class(self.frame_rate, discovered_port, stop_event, device_name, config )

                    assigned_ports[port] = capture_thread_instance
                except socket.gaierror:
                    logger.error("Tracking thread for device '%s' can't bind socket to port %s."
                                "\n-----> Verify that blackhole_config/device_config.ini has the correct port "
                                "assigned for the device, and that another socket is not already listening on that port.", device_name, port)
                    continue

        return [thread for _, thread in assigned_ports.items()]
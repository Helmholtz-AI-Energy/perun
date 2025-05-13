"""ROCM Backend."""

import importlib
import logging
from typing import Callable, Dict, List, Set, Tuple

import numpy as np

from perun.backend.backend import Backend
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Number, Unit
from perun.data_model.sensor import DeviceType, Sensor

log = logging.getLogger(__name__)


class ROCMBackend(Backend):
    """ROCMBackend.

    Initialises sensors to get data from AMD GPUs.
    """

    id = "amdsmi"
    name = "AMD ROCM"
    description: str = "Access GPU information from amd-smi python bindings."

    def setup(self) -> None:
        """Init rocm object."""
        self.amdsmi = importlib.import_module("amdsmi")
        try:
            self.amdsmi.amdsmi_init(self.amdsmi.AmdSmiInitFlags.INIT_AMD_GPUS)
            self._metadata = {
                "amdsmi_version": self.amdsmi.amdsmi_get_lib_version(),
                "source": "AMDSMI",
            }

            device_handles = self.amdsmi.amdsmi_get_processor_handles()
            self._uuid_map = {
                self.amdsmi.amdsmi_get_gpu_device_uuid(handle): handle
                for handle in device_handles
            }
        except self.amdsmi.AmdSmiException as e:
            log.error("Could not initialize AMD SMI")
            log.exception(e)

    def close(self) -> None:
        """Backend cleanup."""
        if hasattr(self, "amdsmi"):
            try:
                self.amdsmi.amdsmi_shut_down()
            except Exception as e:
                log.info(e)

    def availableSensors(self) -> Dict[str, Tuple]:
        """Return string ids of visible devices.

        Returns
        -------
        Set[str]
            Set with sensor ids.
        """
        devices = {}
        for i, (uuid, handle) in enumerate(self._uuid_map.items()):
            try:
                power_info = self.amdsmi.amdsmi_get_power_info(handle)
                if int(power_info["average_socket_power"]) > 0:
                    devices[f"ROCM:{uuid}_POWER"] = (self.id, DeviceType.GPU, Unit.WATT)
            except Exception as e:
                log.info(e)
                log.info(f"Could not get power usage for device rocm:{i} {uuid}")

            try:
                vram_usage = self.amdsmi.amdsmi_get_gpu_memory_usage(
                    handle, self.amdsmi.AmdSmiMemoryType.VRAM
                )
                if vram_usage > 0:
                    devices[f"ROCM:{uuid}_MEM"] = (self.id, DeviceType.GPU, Unit.BYTE)
            except Exception as e:
                log.info(e)
                log.info(f"Could not get memory usage for device rocm:{i} {uuid}")

        return devices

    def getSensors(self, deviceList: Set[str]) -> List[Sensor]:
        """Gather sensor object based on a set of device ids.

        Parameters
        ----------
        deviceList : Set[str]
            Set containing divice ids.

        Returns
        -------
        List[Sensor]
            List with Sensor objects.
        """
        devices = []

        for deviceStr in deviceList:
            id_type = deviceStr.split(":")[1]
            id, measurement_type = id_type.split("_")

            if measurement_type == "POWER":
                devices.append(self._getPowerSensor(id))
            elif measurement_type == "MEM":
                devices.append(self._getMemSensor(id))
        return devices

    def _getPowerSensor(self, d_uuid: str) -> Sensor:
        d_handle = self._uuid_map[d_uuid]
        log.debug(f"Setting up device {d_uuid}")
        board_info = self.amdsmi.amdsmi_get_gpu_board_info(d_handle)

        id = f"ROCM:{d_uuid}"
        name = f"{board_info['product_name']}_{d_uuid}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": d_uuid,
            "name": name,
            **self._metadata,
        }

        power_info = self.amdsmi.amdsmi_get_power_info(d_handle)

        data_type = MetricMetaData(
            Unit.WATT,
            Magnitude.ONE,
            np.dtype("uint32"),
            np.uint32(0),
            np.uint32(int(power_info["power_limit"]) / 10**6),
            np.float32(0),
        )
        return Sensor(
            id + "_POWER",
            device_type,
            device_metadata,
            data_type,
            self._getPowerCallback(d_uuid),
        )

    def _getPowerCallback(self, d_uuid: str) -> Callable[[], Number]:
        handle = self._uuid_map[d_uuid]

        def func() -> Number:
            try:
                power_info = self.amdsmi.amdsmi_get_power_info(handle)
                return np.uint32(power_info["average_socket_power"])
            except Exception as e:
                log.warning(f"Could not get power usage for device {d_uuid}")
                log.exception(e)
                return np.uint32(0)

        return func

    def _getMemSensor(self, d_uuid: str) -> Sensor:
        d_handle = self._uuid_map[d_uuid]
        log.debug(f"Setting up device {d_uuid}")
        board_info = self.amdsmi.amdsmi_get_gpu_board_info(d_handle)

        id = f"ROCM:{d_uuid}"
        name = f"{board_info['product_name']}_{d_uuid}"
        device_type = DeviceType.GPU
        device_metadata = {
            "uuid": d_uuid,
            "name": name,
            **self._metadata,
        }

        max_vram = self.amdsmi.amdsmi_get_gpu_memory_total(
            d_handle, self.amdsmi.AmdSmiMemoryType.VRAM
        )
        max_memory = np.uint64(max_vram)
        data_type = MetricMetaData(
            Unit.BYTE,
            Magnitude.ONE,
            np.dtype("uint64"),
            np.uint64(0),
            max_memory,
            np.uint64(0),
        )
        return Sensor(
            id + "_MEM",
            device_type,
            device_metadata,
            data_type,
            self._getMemCallback(d_uuid),
        )

    def _getMemCallback(self, d_uuid: str) -> Callable[[], Number]:
        handle = self._uuid_map[d_uuid]

        def func() -> Number:
            try:
                vram = self.amdsmi.amdsmi_get_gpu_memory_usage(
                    handle, self.amdsmi.AmdSmiMemoryType.VRAM
                )
                return np.uint64(vram)
            except Exception as e:
                log.warning(f"Could not get memory usage for device {d_uuid}")
                log.exception(e)
                return np.uint64(0)

        return func

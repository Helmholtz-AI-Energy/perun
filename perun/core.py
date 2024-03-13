"""Core perun functionality."""

import logging
import os
import platform
import pprint as pp

# import sys
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

from perun import __version__
from perun.backend.backend import Backend
from perun.backend.nvml import NVMLBackend
from perun.backend.powercap_rapl import PowercapRAPLBackend
from perun.backend.psutil import PSUTILBackend
from perun.backend.rocmsmi import ROCMBackend
from perun.backend.util import getBackendMetadata, getHostMetadata
from perun.comm import Comm
from perun.coordination import getGlobalSensorRankConfiguration, getHostRankDict
from perun.data_model.data import DataNode, NodeType
from perun.io.io import IOFormat, exportTo, importFrom
from perun.monitoring.application import Application
from perun.monitoring.monitor import MonitorStatus, PerunMonitor
from perun.processing import processDataNode
from perun.util import Singleton, getRunId, increaseIdCounter

log = logging.getLogger("perun")


class Perun(metaclass=Singleton):
    """Perun object."""

    def __init__(self, config: ConfigParser) -> None:
        """Init perun with configuration.

        Parameters
        ----------
        config : ConfigParser
            Global configuration object
        """
        self.config = config
        self._comm: Optional[Comm] = None
        self._backends: Optional[Dict[str, Backend]] = None
        self._sensors_config: Optional[List[Dict[str, Set[str]]]] = None
        self._l_sensor_config: Optional[Dict[str, Set[str]]] = None
        self._hostname: Optional[str] = None
        self._host_rank: Optional[Dict[str, List[int]]] = None
        self._l_host_metadata: Optional[Dict[str, Any]] = None
        self._l_backend_metadata: Optional[Dict[str, Any]] = None
        self._monitor: Optional[PerunMonitor] = None
        self.postprocess_callbacks: Dict[str, Callable[[DataNode], None]] = {}
        self.warmup_round: bool = False

    def __del__(self):
        """Perun object destructor."""
        log.info(f"Rank {self.comm.Get_rank()}: __del__ perun")
        self._close_backends()
        log.info(f"Rank {self.comm.Get_rank()}: Exit")

    @property
    def comm(self) -> Comm:
        """Lazy initialization of mpi communication object."""
        if not self._comm:
            os.environ["OMPI_MCA_mpi_warn_on_fork"] = "0"
            os.environ["IBV_FORK_SAFE"] = "1"
            os.environ["RDMAV_FORK_SAFE"] = "1"

            self._comm = Comm()

        return self._comm

    @property
    def hostname(self) -> str:
        """Lazy initialization of hostname.

        Returns
        -------
        str
            Local rank hostname.
        """
        if not self._hostname:
            self._hostname = platform.node()
        return self._hostname

    @property
    def backends(self) -> Dict[str, Backend]:
        """Lazy initialization of backends dictionary.

        Returns
        -------
        Dict[str, Backend]
            Dictionary of available backends.
        """
        if not self._backends:
            self._backends = {}
            classList: Dict[str, Type[Backend]] = {
                "PowercapRAPL": PowercapRAPLBackend,
                "NVML": NVMLBackend,
                "PSUTIL": PSUTILBackend,
                "ROCM": ROCMBackend,
            }
            for name, backend in classList.items():
                try:
                    backend_instance = backend()
                    self._backends[backend_instance.id] = backend_instance
                except ImportError as ie:
                    log.info(f"Missing dependencies for backend {name}")
                    log.info(ie)
                except Exception as e:
                    log.info(f"Unknown error loading dependecy {name}")
                    log.info(e)

        return self._backends

    def _close_backends(self):
        """Close available backends."""
        if self._backends:
            for backend in self._backends.values():
                backend.close()

    @property
    def host_rank(self) -> Dict[str, List[int]]:
        """Lazy initialization of host_rank dictionary.

        Returns
        -------
        Dict[str, List[int]]
            Dictionary with key (hostname) and values (list of ranks in host)
        """
        if not self._host_rank:
            self._host_rank = getHostRankDict(self.comm, self.hostname)

        return self._host_rank

    @property
    def sensors_config(self) -> List[Dict[str, Set[str]]]:
        """Lazy initialization of global sensor configuration.

        Returns
        -------
        List[Dict[str, Set[str]]]
            Global sensor configuration.
        """
        if not self._sensors_config:
            self._sensors_config = getGlobalSensorRankConfiguration(
                self.comm, self.backends, self.host_rank
            )
        return self._sensors_config

    @property
    def l_sensors_config(self) -> Dict[str, Set[str]]:
        """Lazy initialization of local sensor configuration.

        Returns
        -------
        Dict[str, Set[str]]
            Local sensor configuration.
        """
        if not self._l_sensor_config:
            self._l_sensor_config = self.sensors_config[self.comm.Get_rank()]

        return self._l_sensor_config

    @property
    def l_host_metadata(self) -> Dict[str, Any]:
        """Lazy initialization of local metadata dictionary.

        Returns
        -------
        Dict[str, Any]
            Metadata dictionary
        """
        if not self._l_host_metadata:
            self._l_host_metadata = getHostMetadata()
        return self._l_host_metadata

    @property
    def l_backend_metadata(self) -> Dict[str, Any]:
        """Lazy initialization of local metadata dictionary.

        Returns
        -------
        Dict[str, Any]
            Metadata dictionary
        """
        if not self._l_backend_metadata:
            self._l_backend_metadata = getBackendMetadata(
                self.backends, self.l_sensors_config
            )
        return self._l_backend_metadata

    def mark_event(self, region_id: str):
        """
        Mark an event for a specific region.

        Parameters
        ----------
        region_id : str
            The ID of the region to mark the event for.

        Returns
        -------
        None
        """
        if self._monitor:
            self._monitor.local_regions.addEvent(region_id)

    def monitor_application(
        self,
        app: Application,
    ):
        """Execute coordination, monitoring, post-processing, and reporting steps, in that order.

        Parameters
        ----------
        app : Path
            App script file path
        """
        log.debug(f"Rank {self.comm.Get_rank()} Backends: {pp.pformat(self.backends)}")

        starttime = datetime.now()
        app_name = app.name
        multirun_id = getRunId(starttime)

        # Store relevant info in config.
        self.config.set("output", "app_name", app_name)
        self.config.set("output", "run_id", multirun_id)
        self.config.set("output", "starttime", starttime.isoformat())

        log.info(f"App: {app_name}, MR_ID: {multirun_id}")

        backends = self.backends
        l_sensors_config = self.l_sensors_config
        self._monitor = PerunMonitor(
            app, self.comm, backends, l_sensors_config, self.config
        )

        if self.config.getint("benchmarking", "warmup_rounds"):
            log.info(f"Rank {self.comm.Get_rank()} : Started warmup rounds")
            self.warmup_round = True
            for i in range(self.config.getint("benchmarking", "warmup_rounds")):
                log.info(f"Warmup run: {i}")
                status, _ = self._monitor.run_application(str(i), record=False)
                if (
                    status == MonitorStatus.FILE_NOT_FOUND
                    or status == MonitorStatus.SCRIPT_ERROR
                ):
                    return

            self.warmup_round = False

        log.info(f"Rank {self.comm.Get_rank()}: Monitoring start")
        multirun_nodes: Dict[str, DataNode] = {}
        for i in range(self.config.getint("benchmarking", "rounds")):
            status, runNode = self._monitor.run_application(str(i), record=True)

            if status == MonitorStatus.SCRIPT_ERROR:
                if runNode is not None:
                    log.error(f"Rank {self.comm.Get_rank()}: Script error")
                    multirun_nodes[str(i)] = runNode
                    failedRun = self._process_multirun(multirun_nodes)
                    log.error(
                        f"Storing failed run under {self.config.get('output', 'data_out')}/{app.name}"
                    )
                    self._export_multirun(failedRun)

                    log.info(f"Rank {self.comm.Get_rank()}: Aborting mpi context.")
                return
            elif status == MonitorStatus.FILE_NOT_FOUND:
                log.error(f"Rank {self.comm.Get_rank()}: App not found")
                return

            if self.comm.Get_rank() == 0 and runNode:
                runNode.metadata = {**runNode.metadata, **self.l_host_metadata}
                for node in runNode.nodes.values():
                    node.metadata["mpi_ranks"] = self.host_rank[node.id]

                runNode = processDataNode(runNode, self.config)
                multirun_nodes[str(i)] = runNode

        # Get app node data if it exists
        if self.comm.Get_rank() == 0 and len(multirun_nodes) > 0:
            multirun_node = self._process_multirun(multirun_nodes)
            self._export_multirun(multirun_node)
            self._run_postprocess_callbacks(multirun_node)

    def _export_multirun(self, multirun_node: DataNode):
        data_out = Path(self.config.get("output", "data_out"))
        app_name = self.config.get("output", "app_name")
        starttime = self.config.get("output", "starttime")
        out_format = IOFormat(self.config.get("output", "format"))

        multirun_id = multirun_node.id

        app_data_file = data_out / f"{app_name}.{IOFormat.HDF5.suffix}"
        app_data = None
        if app_data_file.exists() and app_data_file.is_file():
            app_data = self.import_from(app_data_file, IOFormat.HDF5)
            app_data.metadata["last_execution_dt"] = starttime
            previous_run_ids = list(app_data.nodes.keys())
            multirun_id = increaseIdCounter(previous_run_ids, multirun_id)
            multirun_node.id = multirun_id
            app_data.nodes[multirun_node.id] = multirun_node
            app_data.processed = False

        else:
            app_data = DataNode(
                app_name,
                NodeType.APP,
                metadata={
                    "creation_dt": starttime,
                    "last_execution_dt": starttime,
                },
                nodes={multirun_id: multirun_node},
                processed=False,
            )
        app_data = processDataNode(app_data, self.config)

        self.export_to(data_out, app_data, IOFormat.HDF5)
        if out_format != IOFormat.HDF5:
            self.export_to(data_out, app_data, out_format, multirun_id)

    def _process_multirun(self, multirun_nodes: Dict[str, DataNode]) -> DataNode:
        app_name = self.config.get("output", "app_name")
        starttime = self.config.get("output", "starttime")
        multirun_id = self.config.get("output", "run_id")

        # Multi_run data processing
        multirun_node = DataNode(
            multirun_id,
            NodeType.MULTI_RUN,
            metadata={
                "app_name": app_name,
                "perun_version": __version__,
                "execution_dt": starttime,
                "n_runs": str(len(multirun_nodes)),
                **{
                    f"{section_name}.{option}": value
                    for section_name in self.config.sections()
                    for option, value in self.config.items(section_name)
                },
            },
            nodes=multirun_nodes,
            processed=False,
        )
        multirun_node = processDataNode(multirun_node, self.config)
        return multirun_node

    def import_from(self, filePath: Path, format: IOFormat) -> DataNode:
        """Import data node from given filepath.

        Parameters
        ----------
        filePath : Path
            Perun data node file path.
        format : IOFormat
            File format.

        Returns
        -------
        DataNode
            Imported DataNode.
        """
        return importFrom(filePath, format)

    def export_to(
        self,
        dataOut: Path,
        dataNode: DataNode,
        format: IOFormat,
        mr_id: Optional[str] = None,
    ):
        """Export data to selected format.

        Parameters
        ----------
        dataOut : Path
            Directory where data will be saved.
        dataNode : DataNode
            Data node to export.
        format : IOFormat
            Format to export data.
        """
        exportTo(dataOut, dataNode, format, mr_id)

    def _run_postprocess_callbacks(self, dataNode: DataNode):
        for name, callback in self.postprocess_callbacks.items():
            log.info(f"Running callback {name}")
            callback(dataNode)

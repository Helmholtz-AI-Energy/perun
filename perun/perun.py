"""Core perun functionality."""
import enum
import logging
import os
import platform
import pprint as pp
import time

# import sys
from configparser import ConfigParser
from datetime import datetime
from multiprocessing import Event, Process, Queue
from multiprocessing.synchronize import Event as EventClass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

from perun import __version__
from perun.backend.backend import Backend
from perun.backend.nvml import NVMLBackend
from perun.backend.powercap_rapl import PowercapRAPLBackend
from perun.backend.psutil import PSUTILBackend
from perun.backend.rocmsmi import ROCMBackend
from perun.backend.util import getBackendMetadata, getHostMetadata
from perun.comm import Comm
from perun.coordination import getGlobalSensorRankConfiguration, getHostRankDict
from perun.data_model.data import DataNode, LocalRegions, NodeType
from perun.io.io import IOFormat, exportTo, importFrom
from perun.processing import processDataNode
from perun.subprocess import perunSubprocess
from perun.util import getRunId, getRunName, increaseIdCounter, singleton

log = logging.getLogger("perun")


class PerunStatus(enum.Enum):
    """DataNode type enum."""

    SETUP = enum.auto()
    RUNNING = enum.auto()
    RUNNING_WARMUP = enum.auto()
    PROCESSING = enum.auto()
    SCRIPT_ERROR = enum.auto()
    SCRIPT_ERROR_WARMUP = enum.auto()
    PERUN_ERROR = enum.auto()
    MPI_ERROR = enum.auto()
    SUCCESS = enum.auto()


@singleton
class Perun:
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
        self.local_regions: Optional[LocalRegions] = None
        self.warmup_round: bool = False
        self.status = PerunStatus.SETUP

        # Subprocess handlers
        self.sp_ready_event: Optional[EventClass] = None
        self.start_event: Optional[EventClass] = None
        self.stop_event: Optional[EventClass] = None

        self.queue: Optional[Queue] = None
        self.perunSP: Optional[Process] = None

    def __del__(self):
        """Perun object destructor."""
        log.info(f"Rank {self.comm.Get_rank()}: __del__ perun")
        self._close_backends()
        log.info(f"Rank {self.comm.Get_rank()}: Exit status {self.status}")
        if self.status != PerunStatus.SUCCESS:
            if (
                self.status == PerunStatus.RUNNING
                or self.status == PerunStatus.RUNNING_WARMUP
            ):
                log.error(
                    f"Rank {self.comm.Get_rank()}: Looks like you are using the exit function to stop your script. This is not recommended, as it interrupts the normal perun execution. No data can be salvaged if the app terminates in this manner."
                )
            elif (
                self.status == PerunStatus.SCRIPT_ERROR
                or self.status == PerunStatus.SCRIPT_ERROR_WARMUP
            ):
                log.error(
                    f"Rank {self.comm.Get_rank()}: Seems like your script terminated early because of an error. Perun will try to collect any available data. Try to fix your script before running with perun to get a more complete stack trace from your script. If the error only happens when running with perun, consider submitting an issue in our github: https://github.com/Helmholtz-AI-Energy/perun"
                )
            elif self.status == PerunStatus.MPI_ERROR:
                log.error(
                    f"Rank {self.comm.Get_rank()}: This should not be reached ever. It's imposible."
                )

            if self.status == PerunStatus.SCRIPT_ERROR:
                availableRanks = self.comm.check_ranks_availability()

                log.error(
                    f"Rank {self.comm.Get_rank()}: Available ranks {availableRanks}"
                )
                # dataNode = self._process_single_run(0, time.time_ns())

            if (
                self.status == PerunStatus.SCRIPT_ERROR
                or self.status == PerunStatus.SCRIPT_ERROR_WARMUP
                or self.status == PerunStatus.RUNNING
                or self.status == PerunStatus.RUNNING_WARMUP
            ):
                log.error(f"Rank {self.comm.Get_rank()}: Aborting mpi context.")
                self.comm.Abort(1)

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

    def monitor_application(
        self,
        app: Path,
    ):
        """Execute coordination, monitoring, post-processing, and reporting steps, in that order.

        Parameters
        ----------
        app : Path
            App script file path
        """
        log.debug(f"Rank {self.comm.Get_rank()} Backends: {pp.pformat(self.backends)}")

        data_out = Path(self.config.get("output", "data_out"))
        out_format = IOFormat(self.config.get("output", "format"))
        starttime = datetime.now()
        app_name = getRunName(app)
        multirun_id = getRunId(starttime)

        log.info(f"App: {app_name}, MR_ID: {multirun_id}")

        if self.config.getint("benchmarking", "warmup_rounds"):
            log.info(f"Rank {self.comm.Get_rank()} : Started warmup rounds")
            self.warmup_round = True
            for i in range(self.config.getint("benchmarking", "warmup_rounds")):
                log.info(f"Warmup run: {i}")
                _ = self._run_application(app, str(i), record=False)

            self.warmup_round = False

        log.info(f"Rank {self.comm.Get_rank()}: Monitoring start")
        multirun_nodes: Dict[str, DataNode] = {}
        for i in range(self.config.getint("benchmarking", "rounds")):
            runNode: Optional[DataNode] = self._run_application(
                app, str(i), record=True
            )
            if self.comm.Get_rank() == 0 and runNode:
                multirun_nodes[str(i)] = runNode

        # Get app node data if it exists
        if self.comm.Get_rank() == 0 and len(multirun_nodes) > 0:
            # Multi_run data processing
            multirun_node = DataNode(
                multirun_id,
                NodeType.MULTI_RUN,
                metadata={
                    "app_name": getRunName(app),
                    "perun_version": __version__,
                    "execution_dt": starttime.isoformat(),
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

            app_data_file = data_out / f"{app_name}.{IOFormat.HDF5.suffix}"
            app_data = None
            if app_data_file.exists() and app_data_file.is_file():
                app_data = self.import_from(app_data_file, IOFormat.HDF5)
                app_data.metadata["last_execution_dt"] = starttime.isoformat()
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
                        "creation_dt": starttime.isoformat(),
                        "last_execution_dt": starttime.isoformat(),
                    },
                    nodes={multirun_id: multirun_node},
                    processed=False,
                )
            app_data = processDataNode(app_data, self.config)

            self.export_to(data_out, app_data, IOFormat.HDF5)
            if out_format != IOFormat.HDF5:
                self.export_to(data_out, app_data, out_format, multirun_id)

        self.status = PerunStatus.SUCCESS

    def _process_single_run(self, run_id: str, starttime_ns: int) -> Optional[DataNode]:
        """Collect data from subprocess and pack it in a data node.

        Parameters
        ----------
        run_id : str
            The id to use for the data node.
        starttime_ns : int
            Start time of the run.

        Returns
        -------
        Optional[DataNode]
            If the rank spawned a subprocess, returns the data node with the data.
        """
        if self.status == PerunStatus.RUNNING:
            self.start_event.set()  # type: ignore
            self.stop_event.set()  # type: ignore
            log.error(
                "You should not use the exit function to exit your script!. Trying to salvage data."
            )

        if self.queue and self.perunSP:
            log.info(f"Rank {self.comm.Get_rank()}: Getting queue contents")
            nodeData = self.queue.get(block=True)
            log.info(f"Rank {self.comm.Get_rank()}: Got queue contents")
            log.info(f"Rank {self.comm.Get_rank()}: Waiting for subprocess to close")
            self.perunSP.join()
            self.perunSP.close()
            log.info(f"Rank {self.comm.Get_rank()}: Subprocess closed")
            self.queue.close()
        else:
            nodeData = None

        log.info(f"Rank {self.comm.Get_rank()}: Exited the subprocess")

        if nodeData:
            nodeData.metadata["mpi_ranks"] = self.host_rank[self.hostname]

        # 5) Collect data from everyone on the first rank
        if self.status == PerunStatus.PROCESSING:
            dataNodes: Optional[List[DataNode]] = self.comm.gather(nodeData, root=0)
            globalRegions: Optional[List[LocalRegions]] = self.comm.gather(
                self.local_regions, root=0
            )

        if dataNodes and globalRegions:
            # 6) On the first rank, create run node
            runNode = DataNode(
                id=run_id,
                type=NodeType.RUN,
                metadata={**self.l_host_metadata},
                nodes={node.id: node for node in dataNodes if node},
            )
            runNode.addRegionData(globalRegions, starttime_ns)
            runNode = processDataNode(runNode, self.config)

            return runNode
        return None

    def _run_application(
        self,
        app: Path,
        run_id: str,
        record: bool = True,
    ) -> Optional[DataNode]:
        log.info(f"Rank {self.comm.Get_rank()}: _run_application")
        if record:
            # 1) Get sensor configuration
            self.sp_ready_event = Event()
            self.start_event = Event()
            self.stop_event = Event()

            self.queue = None
            self.perunSP = None

            # 2) If assigned devices, create subprocess
            if len(self.l_sensors_config.keys()) > 0:
                log.debug(
                    f"Rank {self.comm.Get_rank()} - Local Backendens : {pp.pformat(self.l_sensors_config)}"
                )
                self.queue = Queue()
                self.perunSP = Process(
                    target=perunSubprocess,
                    args=[
                        self.queue,
                        self.comm.Get_rank(),
                        self.backends,
                        self.l_sensors_config,
                        self.config,
                        self.sp_ready_event,
                        self.start_event,
                        self.stop_event,
                        self.config.getfloat("monitor", "sampling_rate"),
                    ],
                )
                self.perunSP.start()
            else:
                self.sp_ready_event.set()  # type: ignore

            # 3) Start application
            try:
                self.sp_ready_event.wait()  # type: ignore
                with open(str(app), "r") as scriptFile:
                    self.local_regions = LocalRegions()
                    self.comm.barrier()
                    log.info(f"Rank {self.comm.Get_rank()}: Started App")
                    self.start_event.set()  # type: ignore
                    starttime_ns = time.time_ns()
                    self.status = PerunStatus.RUNNING
                    exec(
                        scriptFile.read(),
                        {"__name__": "__main__", "__file__": app.name},
                    )
                    self.status = PerunStatus.PROCESSING
                    # run_stoptime = datetime.utcnow()
                    log.info(f"Rank {self.comm.Get_rank()}: App Stopped")
                    self.stop_event.set()  # type: ignore
            except Exception as e:
                self.status = PerunStatus.SCRIPT_ERROR
                log.error(
                    f"Rank {self.comm.Get_rank()}:  Found error on monitored script: {str(app)}"
                )
                s, r = getattr(e, "message", str(e)), getattr(e, "message", repr(e))
                log.error(f"Rank {self.comm.Get_rank()}: {s}")
                log.error(f"Rank {self.comm.Get_rank()}: {r}")
                self.start_event.set()  # type: ignore
                self.stop_event.set()  # type: ignore
                log.error(
                    f"Rank {self.comm.Get_rank()}:  Set start and stop event forcefully"
                )
                self.__del__()

            # 4) App finished, stop subrocess and get data
            return self._process_single_run(run_id, starttime_ns)

        else:
            try:
                with open(str(app), "r") as scriptFile:
                    self.status = PerunStatus.RUNNING_WARMUP
                    exec(
                        scriptFile.read(),
                        {"__name__": "__main__", "__file__": app.name},
                    )
                    self.status = PerunStatus.PROCESSING
            except Exception as e:
                self.status = PerunStatus.SCRIPT_ERROR_WARMUP
                log.error(
                    f"Rank {self.comm.Get_rank()}:  Found error on monitored script: {str(app)}"
                )
                s, r = getattr(e, "message", str(e)), getattr(e, "message", repr(e))
                log.error(f"Rank {self.comm.Get_rank()}: {s}")
                log.error(f"Rank {self.comm.Get_rank()}: {r}")
                self.__del__()
            return None

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

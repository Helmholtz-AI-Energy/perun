"""Core perun functionality."""
import os
import platform
import pprint as pp

# import sys
import types
from configparser import ConfigParser
from datetime import datetime
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from perun import __version__, log
from perun.backend import Backend, IntelRAPLBackend, NVMLBackend, PSUTILBackend
from perun.backend.util import getHostMetadata
from perun.comm import Comm
from perun.coordination import getGlobalSensorRankConfiguration, getHostRankDict
from perun.data_model.data import DataNode, NodeType
from perun.io import io
from perun.io.io import IOFormat, exportTo
from perun.processing import processDataNode
from perun.subprocess import perunSubprocess
from perun.util import getRunId, getRunName, singleton


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
        self._metadata: Optional[Dict] = None
        self._l_metadata: Optional[Dict] = None

    def __del__(self):
        """Perun object destructor."""
        self._close_backends()

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
            classList: List[Type[Backend]] = [
                IntelRAPLBackend,
                NVMLBackend,
                PSUTILBackend,
            ]
            for backend in classList:
                try:
                    backend_instance = backend()
                    self._backends[backend_instance.id] = backend_instance
                except ImportError as ie:
                    log.warning(f"Missing dependencies for backend {backend.__name__}")
                    log.warning(ie)
                except Exception as e:
                    log.warning(f"Unknown error loading dependecy {backend.__name__}")
                    log.warning(e)

        return self._backends

    def _close_backends(self):
        """Close available backends."""
        for backend in self.backends.values():
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
    def l_metadata(self) -> Dict[str, Any]:
        """Lazy initialization of local metadata dictionary.

        Returns
        -------
        Dict[str, Any]
            Metadata dictionary
        """
        if not self._l_metadata:
            self._l_metadata = getHostMetadata(self.backends, self.l_sensors_config)
        return self._l_metadata

    def monitor_application(
        self,
        app: Union[Callable, Path],
        app_args: tuple = tuple(),
        app_kwargs: dict = dict(),
    ):
        """Execute coordination, monitoring, post-processing, and reporting steps, in that order.

        Parameters
        ----------
        app : Path
            App script file path
        app_args : tuple, optional
            App args, by default tuple()
        app_kwargs : dict, optional
            App kwargs, by default dict()
        """
        log.debug(f"Rank {self.comm.Get_rank()} Backends: {pp.pformat(self.backends)}")

        starttime = datetime.utcnow()
        app_results: Optional[Any] = None
        data_out = Path(self.config.get("output", "data_out"))
        format = IOFormat(self.config.get("output", "format"))

        if not self.config.getboolean("benchmarking", "bench_enable"):
            app_results, dataNode = self._run_application(
                app, app_args, app_kwargs, record=True
            )
            if dataNode:
                # Only on first rank, export data
                exportTo(data_out, dataNode, format)
        else:
            # Start with warmup rounds
            log.info(f"Rank {self.comm.Get_rank()} : Started warmup rounds")
            for i in range(self.config.getint("benchmarking", "bench_warmup_rounds")):
                log.info(f"Warmup run: {i}")
                app_results, _ = self._run_application(
                    app, app_args, app_kwargs, record=False
                )

            log.info(f"Rank {self.comm.Get_rank()} : Started bench rounds")
            runNodes: List[DataNode] = []
            for i in range(self.config.getint("benchmarking", "bench_rounds")):
                log.info(f"Rank {self.comm.Get_rank()} : Bench run: {i}")
                app_results, runNode = self._run_application(
                    app, app_args, app_kwargs, record=True, run_id=str(i)
                )
                if runNode:
                    runNodes.append(runNode)

            if len(runNodes) > 0:
                benchNode = DataNode(
                    id=getRunId(starttime),
                    type=NodeType.MULTI_RUN,
                    metadata={
                        "app_name": getRunName(app),
                        "startime": starttime.isoformat(),
                        # "perun_version": __version__,
                    },
                    nodes={node.id: node for node in runNodes},
                )
                benchNode = processDataNode(benchNode)

                exportTo(data_out, benchNode, format)

        return app_results

    def _run_application(
        self,
        app: Union[Callable, Path],
        app_args: tuple = tuple(),
        app_kwargs: dict = dict(),
        record: bool = True,
        run_id: Optional[str] = None,
    ) -> Tuple[Optional[Any], Optional[DataNode]]:
        app_result: Optional[Any] = None

        log.info(f"Rank {self.comm.Get_rank()}: _run_application")
        if record:
            # 1) Get sensor configuration
            start_event = Event()
            stop_event = Event()

            queue: Optional[Queue] = None
            perunSP: Optional[Process] = None

            # 2) If assigned devices, create subprocess
            if len(self.l_sensors_config.keys()) > 0:
                log.debug(
                    f"Rank {self.comm.Get_rank()} - Local Backendens : {pp.pformat(self.l_sensors_config)}"
                )
                queue = Queue()
                perunSP = Process(
                    target=perunSubprocess,
                    args=[
                        queue,
                        start_event,
                        stop_event,
                        self.l_sensors_config,
                        self.config.getfloat("monitor", "sampling_rate"),
                    ],
                )
                perunSP.start()
            else:
                start_event.set()

            # 3) Start application
            if isinstance(app, Path):
                try:
                    with open(str(app), "r") as scriptFile:
                        start_event.wait()
                        self.comm.barrier()
                        log.info(f"Rank {self.comm.Get_rank()}: Started App")
                        run_starttime = datetime.utcnow()
                        exec(
                            scriptFile.read(),
                            {"__name__": "__main__", "__file__": app.name},
                        )
                        log.info(f"Rank {self.comm.Get_rank()}: App Stopped")
                        stop_event.set()
                except Exception as e:
                    log.error(
                        f"Rank {self.comm.Get_rank()}:  Found error on monitored script: {str(app)}"
                    )
                    stop_event.set()
                    raise e

            elif isinstance(app, types.FunctionType):
                try:
                    start_event.wait()
                    self.comm.barrier()
                    log.info(f"Rank {self.comm.Get_rank()}: Started App")
                    run_starttime = datetime.utcnow()

                    app_result = app(*app_args, **app_kwargs)
                    log.info(f"Rank {self.comm.Get_rank()}: Stopped App")
                except Exception as e:
                    stop_event.set()
                    raise e

            # 4) App finished, stop subrocess and get data
            if queue and perunSP:
                log.info(f"Rank {self.comm.Get_rank()}: Getting queue contents")
                nodeData = queue.get(block=True)
                log.info(f"Rank {self.comm.Get_rank()}: Got queue contents")
                log.info(
                    f"Rank {self.comm.Get_rank()}: Waiting for subprocess to close"
                )
                perunSP.join()
                perunSP.close()
                log.info(f"Rank {self.comm.Get_rank()}: Subprocess closed")
                queue.close()
            else:
                nodeData = None

            self.comm.barrier()
            log.info(f"Rank {self.comm.Get_rank()}: Everyone exited the subprocess")

            if nodeData:
                nodeData.metadata["mpi_ranks"] = self.host_rank[self.hostname]

            # 5) Collect data from everyone on the first rank
            dataNodes: Optional[List[DataNode]] = self.comm.gather(nodeData, root=0)
            if dataNodes:
                # 6) On the first rank, create run node
                runNode = DataNode(
                    id=run_id if run_id is not None else getRunId(run_starttime),
                    type=NodeType.RUN,
                    metadata={
                        "app_name": getRunName(app),
                        "startime": run_starttime.isoformat(),
                        "perun_version": __version__,
                    },
                    nodes={node.id: node for node in dataNodes if node},
                )
                runNode = processDataNode(runNode)

                return app_result, runNode
            return app_result, None

        else:
            if isinstance(app, Path):
                # filePath = app
                try:
                    with open(str(app), "r") as scriptFile:
                        exec(
                            scriptFile.read(),
                            {"__name__": "__main__", "__file__": app.name},
                        )
                except Exception as e:
                    log.error(
                        f"Rank {self.comm.Get_rank()}: Found error on monitored script: {str(app)}"
                    )
                    raise e

            elif isinstance(app, types.FunctionType):
                # filePath = Path(sys.argv[0])
                try:
                    app_result = app(*app_args, **app_kwargs)
                except Exception as e:
                    raise e

            return app_result, None

    @staticmethod
    def import_from(filePath: Path, format: IOFormat) -> DataNode:
        """Import Data Node tree from filepath.

        :param filePath: Perun Data file path
        :type filePath: Path
        :param format: File format
        :type format: IOFormat
        :return: Data Node object
        :rtype: DataNode
        """
        return io.importFrom(filePath, format)

    @staticmethod
    def export_to(dataOut: Path, dataNode: DataNode, format: IOFormat):
        """Export existing Data Node object to the selected format.

        :param dataOut: Output file path
        :type dataOut: Path
        :param dataNode: Data Node to write to file
        :type dataNode: DataNode
        :param format: Output file format
        :type format: IOFormat
        """
        io.exportTo(dataOut, dataNode, format)

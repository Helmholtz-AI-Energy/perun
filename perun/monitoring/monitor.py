"""Monitor module."""

import enum
import logging
import multiprocessing
import pprint as pp
import time
from configparser import ConfigParser
from multiprocessing import Event, Process, Queue
from multiprocessing.synchronize import Event as EventClass
from subprocess import Popen
from typing import Any, Dict, List, Optional, Tuple

from perun.backend.backend import Backend
from perun.comm import Comm
from perun.data_model.data import DataNode, LocalRegions, NodeType
from perun.monitoring.subprocess import createNode, perunSubprocess, prepSensors
from perun.processing import processDataNode

from .application import Application

log = logging.getLogger("perun")


class MonitorStatus(enum.Enum):
    """
    Represents the status of a monitor.

    Attributes
    ----------
        SETUP: The monitor is being set up.
        RUNNING: The monitor is running.
        PROCESSING: The monitor is processing data.
        SCRIPT_ERROR: An error occurred in the monitor's script.
        PERUN_ERROR: An error occurred in the Perun system.
        MPI_ERROR: An error occurred in the MPI system.
        FILE_NOT_FOUND: The required file was not found.
        SUCCESS: The monitor completed successfully.
    """

    SETUP = enum.auto()
    RUNNING = enum.auto()
    PROCESSING = enum.auto()
    SCRIPT_ERROR = enum.auto()
    PERUN_ERROR = enum.auto()
    SP_ERROR = enum.auto()
    MPI_ERROR = enum.auto()
    FILE_NOT_FOUND = enum.auto()
    SUCCESS = enum.auto()


class PerunMonitor:
    """
    The PerunMonitor class is responsible for monitoring the application and collecting data.

    Parameters
    ----------
    app : Application
        The application to be monitored.
    comm : Comm
        The communication object for inter-process communication.
    l_sensors_config : Dict[str, Set[str]]
        The configuration for local sensors.
    backends : Dict[str, Backend]
        The backends for data collection.
    config : ConfigParser
        The configuration parser object.

    Attributes
    ----------
    _app : Application
        The application to be monitored.
    _comm : Comm
        The communication object for inter-process communication.
    _l_sensors_config : Dict[str, Tuple]
        The configuration for local sensors.
    _backends : Dict[str, Backend]
        The backends for data collection.
    _config : ConfigParser
        The configuration parser object.
    status : MonitorStatus
        The current status of the monitor.
    """

    def __init__(
        self,
        app: Application,
        comm: Comm,
        backends: Dict[str, Backend],
        l_assigned_sensors: Dict[str, Tuple],
        config: ConfigParser,
    ) -> None:
        self._app = app
        self._comm = comm
        self._backends = backends
        self._l_assigned_sensors = l_assigned_sensors
        self._config = config
        self.status = MonitorStatus.SETUP
        self._reset_subprocess_handlers()

    def _reset_subprocess_handlers(self) -> None:
        """Reset subprocess handlers."""
        self.sp_ready_event: Optional[EventClass] = None
        self.start_event: Optional[EventClass] = None
        self.stop_event: Optional[EventClass] = None

        self.queue: Optional[Queue] = None
        self.perunSP: Optional[Process] = None

    def run_application(
        self,
        run_id: str,
        record: bool = True,
    ) -> Tuple[MonitorStatus, Optional[DataNode], Any]:
        """
        Run the application and returns the monitor status and data node.

        Parameters
        ----------
        run_id : str
            The ID of the run.
        record : bool, optional
            Whether to record data or not. Defaults to True.

        Returns
        -------
        Tuple[MonitorStatus, Optional[DataNode], Any]
            A tuple containing the monitor status and the data node, and the application result.

        Raises
        ------
        SystemExit
            If the application exits using exit(), quit(), or sys.exit().
        Exception
            If an error occurs in the monitored script.

        Notes
        -----
        - If `record` is True, the method performs the following steps:
            1. Gets the sensor configuration.
            2. If there are assigned devices, creates a subprocess to run the application.
            3. Starts the application and waits for it to be ready.
            4. Runs the application.
            5. Stops the application and retrieves the data.
        - If `record` is False, the method simply runs the application without recording data.

        """
        log.info(f"Rank {self._comm.Get_rank()}: _run_application")
        if record:
            if self._app.is_binary:
                return self._run_binary_app(run_id)
            else:
                return self._run_python_app(run_id)
        else:
            try:
                self.status = MonitorStatus.RUNNING
                result = self._app.run()
                self.status = MonitorStatus.PROCESSING
            except SystemExit:
                self.status = MonitorStatus.PROCESSING
                log.warning(
                    "The application exited using exit(), quit() or sys.exit(). This is not the recommended way to exit an application, as it complicates the data collection process. Please refactor your code."
                )
            except Exception as e:
                self.status = MonitorStatus.SCRIPT_ERROR
                result = None
                log.error(
                    f"Rank {self._comm.Get_rank()}:  Found error on monitored application: {str(self._app)}"
                )
                s, r = getattr(e, "message", str(e)), getattr(e, "message", repr(e))
                log.error(f"Rank {self._comm.Get_rank()}: {s}")
                log.error(f"Rank {self._comm.Get_rank()}: {r}")
            return self.status, None, result

    def _run_python_app(
        self, run_id: str
    ) -> Tuple[MonitorStatus, Optional[DataNode], Any]:
        # 1) Get sensor configuration
        self.sp_ready_event = Event()
        self.start_event = Event()
        self.stop_event = Event()

        self.queue = None
        self.perunSP = None

        # 2) If assigned devices, create subprocess
        if len(self._l_assigned_sensors.keys()) > 0:
            log.debug(
                f"Rank {self._comm.Get_rank()} - Local Backendens : {pp.pformat(self._l_assigned_sensors)}"
            )
            self.queue = Queue()
            log.info(
                f"Rank {self._comm.Get_rank()}: {self.queue}, {self._backends}, {self._l_assigned_sensors}, {self._config}, {self.sp_ready_event}, {self.start_event}, {self.stop_event}, {self._config.getfloat('monitor', 'sampling_period')}"
            )
            self.perunSP = Process(
                target=perunSubprocess,
                args=[
                    self.queue,
                    self._comm.Get_rank(),
                    self._backends,
                    self._l_assigned_sensors,
                    self._config,
                    self.sp_ready_event,
                    self.start_event,
                    self.stop_event,
                    self._config.getfloat("monitor", "sampling_period"),
                ],
            )
            log.info(f"Rank {self._comm.Get_rank()}: Starting monitoring subprocess")
            self.perunSP.start()
            log.debug(f"Rank {self._comm.Get_rank()}: Alive: {self.perunSP.is_alive()}")
            log.debug(f"Rank {self._comm.Get_rank()}: SP PID: {self.perunSP.pid}")
            log.debug(
                f"Rank {self._comm.Get_rank()}: SP Exit Code: {self.perunSP.exitcode}"
            )
            log.info(f"Rank {self._comm.Get_rank()}: Monitoring subprocess started")
        else:
            self.sp_ready_event.set()  # type: ignore

        event_set = self.sp_ready_event.wait(30)  # type: ignore
        if self.perunSP and not event_set:
            log.error(
                f"Rank {self._comm.Get_rank()}: Children: {multiprocessing.active_children()}"
            )
            log.error(
                f"Rank {self._comm.Get_rank()}: Monitoring subprocess did not start in time"
            )
            log.error(f"Rank {self._comm.Get_rank()}: Alive: {self.perunSP.is_alive()}")
            log.error(f"Rank {self._comm.Get_rank()}: SP PID: {self.perunSP.pid}")
            log.error(f"Rank {self._comm.Get_rank()}: SP Exit Code: {self.perunSP}")
            self.status = MonitorStatus.SP_ERROR
            self._close_subprocess()

        log.info(f"Rank {self._comm.Get_rank()}: Waiting for everyones status")
        self.all_status = self._comm.allgather(self.status)
        if MonitorStatus.SP_ERROR in self.all_status:
            log.error(f"Rank {self._comm.Get_rank()}: Stopping run")
            log.error(
                f"Rank {self._comm.Get_rank()}: Children: {multiprocessing.active_children()}"
            )

            self.status = MonitorStatus.SP_ERROR
            self._reset_subprocess_handlers()

            return self.status, None, None

        # 3) Start application
        log.info(f"Rank {self._comm.Get_rank()}: Starting App")
        self.local_regions = LocalRegions()
        self.status = MonitorStatus.RUNNING
        self.start_event.set()  # type: ignore
        starttime_ns = time.time_ns()
        try:
            app_result = self._app.run()
        except SystemExit:
            log.info(
                "The application exited using exit(), quit() or sys.exit(). This is not the recommended way to exit an application, as it complicates the data collection process. Please refactor your code."
            )

        except Exception as e:
            self.status = MonitorStatus.SCRIPT_ERROR
            log.error(
                f"Rank {self._comm.Get_rank()}:  Found error on monitored script: {str(self._app)}"
            )
            s, r = getattr(e, "message", str(e)), getattr(e, "message", repr(e))
            log.error(f"Rank {self._comm.Get_rank()}: {s}")
            log.error(f"Rank {self._comm.Get_rank()}: {r}")
            self.stop_event.set()  # type: ignore
            log.error(
                f"Rank {self._comm.Get_rank()}:  Set start and stop event forcefully"
            )
            recoveredNodes = self._handle_failed_run()
            return self.status, recoveredNodes, None

        self.status = MonitorStatus.PROCESSING
        # run_stoptime = datetime.utcnow()
        log.info(f"Rank {self._comm.Get_rank()}: App Stopped")
        self.stop_event.set()  # type: ignore

        # 4) App finished, stop subrocess and get data
        return self.status, self._process_single_run(run_id, starttime_ns), app_result

    def _run_binary_app(
        self, run_id: str
    ) -> Tuple[MonitorStatus, Optional[DataNode], Any]:
        # 1) Prepare sensors
        (
            timesteps,
            t_metadata,
            rawValues,
            lSensors,
        ) = prepSensors(self._backends, self._l_assigned_sensors)
        log.debug(f"SP: backends -- {self._backends}")
        log.debug(f"SP: l_sensor_config -- {self._l_assigned_sensors}")
        log.debug(f"Rank {self._comm.Get_rank()}: perunSP lSensors: {lSensors}")

        sampling_period = self._config.getfloat("monitor", "sampling_period")

        # 2) Start monitoring process
        starttime_ns = time.time_ns()
        process = Popen([self._app.name, *self._app.args])

        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())

        exitCode = process.poll()

        while not isinstance(exitCode, int):
            time.sleep(sampling_period)
            timesteps.append(time.time_ns())
            for idx, device in enumerate(lSensors):
                rawValues[idx].append(device.read())

            exitCode = process.poll()

        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())
        log.info(f"Rank {self._comm.Get_rank()}: App Stopped with exit code {exitCode}")

        # 3) Create data node
        hostNode = createNode(timesteps, t_metadata, rawValues, lSensors, self._config)
        processDataNode(hostNode, self._config)
        globalRegions = [LocalRegions()]

        # 4) Collect data from everyone on the first rank
        runNode = DataNode(id=run_id, type=NodeType.RUN, nodes={hostNode.id: hostNode})
        runNode.addRegionData(globalRegions, starttime_ns)

        return MonitorStatus.SUCCESS, runNode, None

    def _handle_failed_run(self) -> Optional[DataNode]:
        availableRanks = self._comm.check_available_ranks()

        log.error(f"Rank {self._comm.Get_rank()}: Available ranks {availableRanks}")
        try:
            recoverdNodes = self._process_single_run(
                str("failed"), time.time_ns(), available_ranks=availableRanks
            )
        except ValueError:
            log.error(
                "Non of the available ranks have any monitoring data. Closing without generating a report."
            )
            return None
        else:
            if recoverdNodes:
                # Mark run as failed in the configuration
                app_name = "failed_" + self._config.get("output", "app_name")
                self._config.set("output", "app_name", app_name)
                # self.config.set("output", "run_id", "failed_" + self.config.get("output", "run_id"))
                return recoverdNodes
        return None

    def _process_single_run(
        self,
        run_id: str,
        starttime_ns: int,
        available_ranks: Optional[List[int]] = None,
    ) -> Optional[DataNode]:
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
        if self.queue and self.perunSP:
            log.info(f"Rank {self._comm.Get_rank()}: Collecting queue data.")
            nodeData = self.queue.get(block=True)
            log.info(f"Rank {self._comm.Get_rank()}: Closing subprocess.")
            self._close_subprocess()
        else:
            nodeData = None
            self._reset_subprocess_handlers()

        log.info(f"Rank {self._comm.Get_rank()}: Gathering data.")

        # 5) Collect data from everyone on the first rank
        dataNodes: Optional[List[DataNode]] = None
        globalRegions: Optional[List[LocalRegions]] = None
        if not available_ranks:
            dataNodes = self._comm.gather(nodeData, root=0)
            globalRegions = self._comm.gather(self.local_regions, root=0)
        else:
            dataNodes = self._comm.gather_from_ranks(
                nodeData, ranks=available_ranks, root=available_ranks[0]
            )
            globalRegions = self._comm.gather_from_ranks(
                self.local_regions, ranks=available_ranks, root=available_ranks[0]
            )

        if dataNodes and globalRegions:
            dataNodesDict = {node.id: node for node in dataNodes if node}
            if len(dataNodesDict) == 0:
                log.error(f"Rank {self._comm.Get_rank()}: No rank reported any data.")
                raise ValueError("Could not collect data from any rank.")

            # 6) On the first rank, create run node
            runNode = DataNode(
                id=run_id,
                type=NodeType.RUN,
                nodes=dataNodesDict,
            )
            runNode.addRegionData(globalRegions, starttime_ns)

            return runNode
        return None

    def _close_subprocess(self) -> None:
        """Close the subprocess."""
        if self.perunSP and self.queue:
            self.perunSP.join(30)
            if self.perunSP.exitcode is None:
                log.warning(
                    f"Rank {self._comm.Get_rank()}: Monitoring subprocess did not close in time, terminating."
                )
                self.perunSP.terminate()
                self.perunSP.join()
                if self.perunSP.exitcode and self.perunSP.exitcode != 0:
                    log.warning(
                        f"Rank {self._comm.Get_rank()}: Monitoring subprocess exited with code {self.perunSP.exitcode}"
                    )

            self.queue.close()
            self.queue = None
            log.info(f"Rank {self._comm.Get_rank()}: Monitoring subprocess closed")

        self._reset_subprocess_handlers()

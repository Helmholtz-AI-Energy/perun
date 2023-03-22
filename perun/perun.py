"""Core perun functionality."""
import platform
import pprint as pp

# import sys
import time
import types
from datetime import datetime
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from perun import COMM_WORLD, __version__, log
from perun.configuration import config
from perun.coordination import getLocalSensorRankConfiguration
from perun.data_model.data import DataNode, NodeType, RawData
from perun.data_model.measurement_type import Magnitude, MetricMetaData, Unit
from perun.data_model.sensor import DeviceType, Sensor
from perun.io.io import IOFormat, exportTo
from perun.processing import processDataNode, processSensorData
from perun.util import getRunId, getRunName


def monitor_application(
    app: Union[Path, Callable], app_args: tuple = tuple(), app_kwargs: dict = dict()
) -> Optional[Any]:
    """Execute coordination, monitoring, post-processing, and reporting steps, in that order.

    Raises:
        executionError: From cmd line execution, raises any error found on the monitored app.
        functionError:  From decorator execution, raises any error found on the monitored method.

    Returns:
        Optional[Any]: In decorator mode, return the output of the decorated method.
    """
    # outPath: Path = Path(config.get("output", "data_out"))

    # Get node devices
    from perun.backend import backends

    log.debug(f"Backends: {backends}")

    starttime = datetime.utcnow()
    app_results: Optional[Any] = None
    data_out = Path(config.get("output", "data_out"))
    format = IOFormat(config.get("output", "format"))
    includeRawData = config.getboolean("output", "raw")
    depthStr = config.get("output", "depth")
    if depthStr:
        depth = int(depthStr)
    else:
        depth = None

    if not config.getboolean("benchmarking", "bench_enable"):
        app_results, dataNode = _run_application(
            backends, app, app_args, app_kwargs, record=True
        )
        if dataNode:
            # Only on first rank, export data
            exportTo(data_out, dataNode, format, includeRawData, depth)
    else:
        # Start with warmup rounds
        log.info("Started warmup rounds")
        for i in range(config.getint("benchmarking", "bench_warmup_rounds")):
            log.debug(f"Warmup run: {i}")
            app_results, _ = _run_application(
                backends, app, app_args, app_kwargs, record=False
            )

        log.info("Started bench rounds")
        runNodes: List[DataNode] = []
        for i in range(config.getint("benchmarking", "bench_rounds")):
            log.debug(f"Bench run: {i}")
            app_results, runNode = _run_application(
                backends, app, app_args, app_kwargs, record=True, run_id=str(i)
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
                    "perun_version": __version__,
                },
                nodes={node.id: node for node in runNodes},
            )
            benchNode = processDataNode(benchNode)

            exportTo(data_out, benchNode, format, includeRawData, depth)

    for backend in backends:
        backend.close()

    return app_results


def _run_application(
    backends: List,
    app: Union[Path, Callable],
    app_args: tuple = tuple(),
    app_kwargs: dict = dict(),
    record: bool = True,
    run_id: Optional[str] = None,
) -> Tuple[Optional[Any], Optional[DataNode]]:
    app_result: Optional[Any] = None
    if record:
        # 1) Get sensor configuration
        mpiRanks, localBackends = getLocalSensorRankConfiguration(COMM_WORLD, backends)

        start_event = Event()
        stop_event = Event()

        queue: Optional[Queue] = None
        perunSP: Optional[Process] = None

        # 2) If assigned devices, create subprocess
        if len(localBackends.keys()) > 0:
            log.debug(
                f"Rank {COMM_WORLD.Get_rank()} - Local Backendens : {pp.pformat(localBackends)}"
            )
            queue = Queue()
            perunSP = Process(
                target=perunSubprocess,
                args=[
                    queue,
                    start_event,
                    stop_event,
                    localBackends,
                    config.getfloat("monitor", "sampling_rate"),
                ],
            )
            perunSP.start()

        # 3) Start application
        run_starttime = datetime.utcnow()

        if isinstance(app, Path):
            try:
                with open(str(app), "r") as scriptFile:
                    start_event.wait()
                    exec(
                        scriptFile.read(),
                        {"__name__": "__main__", "__file__": app.name},
                    )
                    stop_event.set()
            except Exception as e:
                log.error(f"Found error on monitored script: {str(app)}")
                stop_event.set()
                raise e

        elif isinstance(app, types.FunctionType):
            try:
                start_event.wait()
                app_result = app(*app_args, **app_kwargs)
            except Exception as e:
                stop_event.set()
                raise e
            stop_event.set()

        # 4) App finished, stop subrocess and get data
        if queue and perunSP:
            log.debug("Getting queue contents")
            nodeData = queue.get(block=True)
            log.debug("Got queue contents")
            log.debug("Waiting for subprocess to close")
            perunSP.join()
            perunSP.close()
            log.debug("Subprocess closed")
            queue.close()
        else:
            nodeData = None

        COMM_WORLD.barrier()
        log.debug("Everyone exited the subprocess")

        if nodeData:
            nodeData.metadata["mpi_ranks"] = mpiRanks

        # 5) Collect data from everyone on the first rank
        dataNodes: Optional[List[DataNode]] = COMM_WORLD.gather(nodeData, root=0)
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
                log.error(f"Found error on monitored script: {str(app)}")
                raise e

        elif isinstance(app, types.FunctionType):
            # filePath = Path(sys.argv[0])
            try:
                app_result = app(*app_args, **app_kwargs)
            except Exception as e:
                raise e

        return app_result, None


def perunSubprocess(
    queue: Queue,
    start_event,
    stop_event,
    backendConfig: Dict[str, Set[str]],
    sampling_rate: float,
):
    """
    Parallel function that samples energy values from hardware libraries.

    Args:
        queue (Queue): multiprocessing Queue object where the results are sent after finish
        start_event (_type_): Marks that perun finished setting up and started sampling from devices
        stop_event (_type_): Signal the subprocess that the monitored processed has finished
        deviceIds (Set[str]): List of device ids to sample from
        sampling_rate (int): Sampling rate in s
    """
    from perun.backend import backends

    lSensors: List[Sensor] = []
    for backend in backends:
        backend.setup()
        if backend.name in backendConfig:
            lSensors += backend.getSensors(backendConfig[backend.name])

    timesteps = []
    t_mT = MetricMetaData(
        Unit.SECOND,
        Magnitude.ONE,
        np.dtype("float32"),
        np.float32(0),
        np.finfo("float32").max,
        np.float32(-1),
    )
    rawValues: List[List[np.number]] = []
    for _ in lSensors:
        rawValues.append([])

    log.debug(f"perunSP lSensors: {lSensors}")

    start_event.set()
    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    while not stop_event.wait(sampling_rate):
        timesteps.append(time.time_ns())
        for idx, device in enumerate(lSensors):
            rawValues[idx].append(device.read())

    timesteps.append(time.time_ns())
    for idx, device in enumerate(lSensors):
        rawValues[idx].append(device.read())

    log.debug("Subprocess: Stop event received.")
    for backend in backends:
        backend.close()

    log.debug("Subprocess: Closed backends")
    sensorNodes: Dict = {}

    t_s = np.array(timesteps)
    t_s -= t_s[0]
    t_s = t_s.astype("float32")
    t_s *= 1e-9

    for sensor, values in zip(lSensors, rawValues):
        if sensor.type not in sensorNodes:
            sensorNodes[sensor.type] = []

        dn = DataNode(
            id=sensor.id,
            type=NodeType.SENSOR,
            metadata=sensor.metadata,
            deviceType=sensor.type,
            raw_data=RawData(t_s, np.array(values), t_mT, sensor.dataType),
        )
        # Apply processing to sensor node
        dn = processSensorData(dn)
        sensorNodes[sensor.type].append(dn)

    log.debug("Subprocess: Preprocessed Sensor Data")
    deviceGroupNodes = []
    for deviceType, sensorNodes in sensorNodes.items():
        if deviceType != DeviceType.NODE:
            dn = DataNode(
                id=deviceType.value,
                type=NodeType.DEVICE_GROUP,
                metadata={},
                nodes={sensor.id: sensor for sensor in sensorNodes},
                deviceType=deviceType,
            )

            dn = processDataNode(dn)
            deviceGroupNodes.append(dn)
        else:
            deviceGroupNodes.extend(sensorNodes)

    log.debug("Subprocess: Preprocessed Device Data")

    hostNode = DataNode(
        id=platform.node(),
        type=NodeType.NODE,
        metadata={},
        nodes={node.id: node for node in deviceGroupNodes},
    )
    processDataNode(hostNode)

    # This should send a single processed node for the current computational node
    queue.put(hostNode, block=True)
    log.debug("Subprocess: Sent data")

    for backend in backends:
        backend.close()

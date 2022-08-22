"""Connection to HoreKa hardware measurements."""
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import List, Union

import pandas as pd
from influxdb_client import InfluxDBClient
from mpi4py.MPI import Comm

query = """from(bucket: "hk-collector")
|> range(start: _start, stop: _stop)
|> filter(fn: (r) => r["hostname"] == _node)
|> filter(fn: (r) => r["_measurement"] == "consumed_watts" or r["_measurement"] == "nv_power_usage")
|> pivot(rowKey: ["_time"], columnKey: ["_measurement"], valueColumn: "_value")"""


def get_horeka_measurements(
    comm: Comm, outdir: Path, expName: str, expId: int, start: datetime, stop: datetime
):
    """
    Read hardware data from an Influx Database.

    Args:
        comm (Comm): MPI Communication Object
        outdir (Path): Result location
        expName (str): Experiment name
        expId (int): Experiment Id
        start (datetime): Experiment start time
        stop (datetime): Experiment end time
    """
    URL = os.environ["INFLUXDB_URL"]
    TOKEN = os.environ["INFLUXDB_TOKEN"]
    ORG = os.environ["INFLUXDB_ORG"]
    nodename = platform.node().replace(".localdomain", "")

    idb = InfluxDBClient(url=URL, token=TOKEN, org=ORG)

    now = datetime.now()
    p = {"_start": start - now, "_stop": stop - now, "_node": nodename}

    outpath = outdir / "horeka" / expName / str(expId)

    if comm.rank == 0:
        if not outpath.exists():
            outpath.mkdir(parents=True)

    dfList: Union[List[pd.DataFrame], pd.DataFrame] = idb.query_api().query_data_frame(
        query=query, params=p
    )

    if isinstance(dfList, List):
        for index, df in enumerate(dfList):
            df.to_csv(outpath / f"{nodename}_{index}.csv")
    else:
        dfList.to_csv(outpath / f"{nodename}.csv")

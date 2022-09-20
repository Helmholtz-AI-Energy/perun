"""Connection to HoreKa hardware measurements."""
from datetime import datetime
from pathlib import Path
from typing import List, Union

import pandas as pd
from influxdb_client import InfluxDBClient
from mpi4py.MPI import Comm

from perun import config

query = """from(bucket: "hk-collector")
|> range(start: _start, stop: _stop)
|> filter(fn: (r) => r["hostname"] == _node)
|> filter(fn: (r) => r["_measurement"] == "consumed_watts" or r["_measurement"] == "nv_power_usage")
|> pivot(rowKey: ["_time"], columnKey: ["_measurement"], valueColumn: "_value")"""


def get_horeka_measurements(
    comm: Comm,
    nodeNames: List[str],
    outdir: Path,
    expName: str,
    expId: int,
    start: datetime,
    stop: datetime,
):
    """
    Read hardware data from an Influx Database.

    Args:
        comm (Comm): MPI Communication Object
        nodenames (List[str]): List of node names
        outdir (Path): Result location
        expName (str): Experiment config.get("horeka", "org")
        expId (int): Experiment Id
        start (datetime): Experiment start time
        stop (datetime): Experiment end time
    """
    URL = config.get("horeka", "url")
    TOKEN = config.get("horeka", "token")
    ORG = config.get("horeka", "org")

    idb = InfluxDBClient(url=URL, token=TOKEN, org=ORG, timeout=10000, debug=True)
    if not idb.ready():
        raise Exception("InfluxDB not available/ready")

    outpath = outdir / "horeka" / expName / str(expId)

    for node in nodeNames:
        now = datetime.now()

        p = {"_start": start - now, "_stop": stop - now, "_node": node}
        print(p)

        if not outpath.exists():
            outpath.mkdir(parents=True)

        dfList: Union[
            List[pd.DataFrame], pd.DataFrame
        ] = idb.query_api().query_data_frame(query=query, params=p)
        print(dfList)

        if isinstance(dfList, List):
            for index, df in enumerate(dfList):
                df.to_csv(outpath / f"{node}_{index}.csv")
        else:
            dfList.to_csv(outpath / f"{node}.csv")

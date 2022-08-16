"""Connection to HoreKa hardware measurements."""
from datetime import datetime

import pandas as pd
from influxdb_client import InfluxDBClient


class HoreKaDB:
    """InfluxDB client for the HoreKa hardware measurements."""

    def __init__(self, url: str, token: str, org: str):
        """Create influxdb client object."""
        self.idb = InfluxDBClient(url=url, token=token, org=org)

    def getNodeData(
        self, nodename: str, starttime: datetime, endtime: datetime
    ) -> pd.Dataframe:
        """Query influxDB for node information within a time range."""
        query = f'from(bucket: "hk-collector") \
            |> range(start: {starttime}, end: {endtime}) \
            |> filter(fn: (r) => r["hostname"] == "{nodename}") \
            |> filter(fn: (r) => r["_measurement"] == "consumed_watts" or r["_measurement"] == "nv_power_usage")'

        return self.idb.query_api().query_data_frame(query=query)

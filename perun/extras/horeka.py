"""Connection to HoreKa hardware measurements."""
from datetime import datetime, timedelta

import pandas as pd
from influxdb_client import InfluxDBClient

query = """from(bucket: "hk-collector")
|> range(start: _start, stop: _stop)
|> filter(fn: (r) => r["hostname"] == _node)
|> filter(fn: (r) => r["_measurement"] == "consumed_watts" or r["_measurement"] == "nv_power_usage")"""
# |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "value")'''


class HoreKaDB:
    """InfluxDB client for the HoreKa hardware measurements."""

    def __init__(self, url: str, token: str, org: str):
        """Create influxdb client object."""
        self.idb = InfluxDBClient(url=url, token=token, org=org)

    def getNodeData(
        self, nodename: str, starttime: datetime, endtime: datetime
    ) -> pd.DataFrame:
        """Query influxDB for node information within a time range."""
        now = datetime.utcnow()
        print(timedelta(hours=-1))
        print(now - starttime)
        print((now - endtime))

        p = {"_start": starttime - now, "_stop": endtime - now, "_node": nodename}

        return self.idb.query_api().query(query=query, params=p)

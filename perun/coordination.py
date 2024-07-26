"""Coordination module."""

import logging
from typing import Dict, List, Tuple

from perun.comm import Comm

log = logging.getLogger("perun")


def getHostRankDict(comm: Comm, hostname: str) -> Dict[str, List[int]]:
    """Return a dictionary with all the host names with each MPI rank in them.

    Parameters
    ----------
    comm : Comm
        MPI Communicator
    hostname : str
        Local rank Hostname

    Returns
    -------
    Dict[str, List[int]]
        Global host and mpi ranks dictionary.
    """
    rank = comm.Get_rank()

    gHostRank: List[Tuple[str, int]] = comm.allgather((hostname, rank))
    hostRankDict: Dict[str, List[int]] = {}
    for h, r in gHostRank:
        if h in hostRankDict:
            hostRankDict[h].append(r)
        else:
            hostRankDict[h] = [r]

    return hostRankDict


def assignSensors(
    host_rank_dict: Dict[str, List[int]],
    g_available_sensors: List[Dict[str, Tuple]],
) -> List[Dict[str, Tuple]]:
    """Assings each mpi rank a sensor based on available backends and Host to rank mapping.

    Parameters
    ----------
    host_rank_dict : Dict[str, List[int]]
        Host to rank mapping.
    g_available_sensors : List[Dict[str, Tuple]]
        List of available sensors for each backend for each rank.

    Returns
    -------
    List[Dict[str, Tuple]]
        List with apointed backend and sensors for each MPI rank.
    """
    g_assigned_sensors: List[Dict[str, Tuple]] = [
        {} for _ in range(len(g_available_sensors))
    ]
    for _, ranks in host_rank_dict.items():
        firstRank = sorted(ranks)[0]
        merged_sensors: Dict[str, Tuple] = {}
        for rank in ranks:
            merged_sensors.update(g_available_sensors[rank])

        g_assigned_sensors[firstRank] = merged_sensors
    return g_assigned_sensors

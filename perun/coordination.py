"""Coordination module."""

import logging

from perun.comm import Comm

log = logging.getLogger(__name__)


def getHostRankDict(comm: Comm, hostname: str) -> dict[str, list[int]]:
    """Return a dictionary with all the host names with each MPI rank in them.

    Parameters
    ----------
    comm : Comm
        MPI Communicator
    hostname : str
        Local rank Hostname

    Returns
    -------
    dict[str, list[int]]
        Global host and mpi ranks dictionary.
    """
    rank = comm.Get_rank()

    gHostRank: list[tuple[str, int]] = comm.allgather((hostname, rank))
    hostRankDict: dict[str, list[int]] = {}
    for h, r in gHostRank:
        if h in hostRankDict:
            hostRankDict[h].append(r)
        else:
            hostRankDict[h] = [r]

    return hostRankDict


def assignSensors(
    host_rank_dict: dict[str, list[int]],
    g_available_sensors: list[dict[str, tuple]],
) -> list[dict[str, tuple]]:
    """Assings each mpi rank a sensor based on available backends and Host to rank mapping.

    Parameters
    ----------
    host_rank_dict : dict[str, list[int]]
        Host to rank mapping.
    g_available_sensors : list[dict[str, tuple]]
        List of available sensors for each backend for each rank.

    Returns
    -------
    list[dict[str, tuple]]
        List with apointed backend and sensors for each MPI rank.
    """
    g_assigned_sensors: list[dict[str, tuple]] = [
        {} for _ in range(len(g_available_sensors))
    ]
    for _, ranks in host_rank_dict.items():
        firstRank = sorted(ranks)[0]
        merged_sensors: dict[str, tuple] = {}
        for rank in ranks:
            merged_sensors.update(g_available_sensors[rank])

        g_assigned_sensors[firstRank] = merged_sensors
    return g_assigned_sensors

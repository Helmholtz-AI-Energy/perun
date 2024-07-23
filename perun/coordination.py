"""Coordination module."""

import functools
import logging
import pprint as pp
from typing import Dict, List, Set, Tuple

from perun.backend.backend import Backend
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
    g_available_sensors: List[Dict[str, Tuple[str]]],
    selected_backends: List[str],
    selected_sensors: List[str],
) -> List[Dict[str, Tuple[str]]]:
    """Assings each mpi rank a sensor based on available backends and Host to rank mapping.

    Parameters
    ----------
    host_rank_dict : Dict[str, List[int]]
        Host to rank mapping.
    g_available_sensors : List[Dict[str, Tuple[str]]]
        List of available sensors for each backend for each rank.
    selected_backends : List[str]
        List of selected backends.
    selected_sensors : List[str]
        List of selected sensors.

    Returns
    -------
    List[Dict[str, Set[str]]]
        List with apointed backend and sensors for each MPI rank.
    """
    g_assigned_sensors = [{} for _ in range(len(g_available_sensors))]
    for host, ranks in host_rank_dict.items():
        firstRank = sorted(ranks)[0]
        merged_sensors = functools.reduce(
            lambda x, y: x | g_available_sensors[y], ranks, {}
        )

        if len(selected_backends) > 0 and len(selected_sensors) > 0:
            merge_sensors = {
                k: v
                for k, v in merge_sensors.items()
                if (v[0] in selected_backends) and (k in selected_sensors)
            }
        elif len(selected_sensors) > 0:
            merge_sensors = {
                k: v for k, v in merge_sensors.items() if k in selected_sensors
            }
        elif len(selected_backends) > 0:
            merge_sensors = {
                k: v for k, v in merge_sensors.items() if v[0] in selected_backends
            }

        g_assigned_sensors[firstRank] = merged_sensors
    return g_assigned_sensors

"""Coordination module."""

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


def getGlobalSensorRankConfiguration(
    comm: Comm, backends: Dict[str, Backend], globalHostRanks: Dict[str, List[int]]
) -> List[Dict[str, Set[str]]]:
    """Gather available sensor information from every MPI rank and assign/unassign sensors to each rank to avoid over sampling.

    Parameters
    ----------
    comm : Comm
        MPI Communicator
    backends : Dict[str, Backend]
        Backend dictionary
    globalHostRanks : Dict[str, List[int]]
        Mapping from host to MPI ranks

    Returns
    -------
    List[Dict[str, Set[str]]]
        List with apointed backend and sensors for each MPI rank.
    """
    visibleSensorsByBackend: Dict[str, Set[str]] = {
        backend.name: backend.visibleSensors() for backend in backends.values()
    }
    log.debug(
        f"Rank {comm.Get_rank()} : Visible devices = {pp.pformat(visibleSensorsByBackend)}"
    )
    globalVisibleSensorsByBackend = comm.allgather(visibleSensorsByBackend)
    globalSensorConfig = assignSensors(globalVisibleSensorsByBackend, globalHostRanks)
    return globalSensorConfig


def assignSensors(
    hostBackends: List[Dict[str, Set[str]]], hostNames: Dict[str, List[int]]
) -> List[Dict[str, Set[str]]]:
    """Assings each mpi rank a sensor based on available backends and Host to rank mapping.

    Parameters
    ----------
    hostBackends : List[Dict[str, Set[str]]]
        List with global backends
    hostNames : Dict[str, List[int]]
        Host to MPI Rank mapping

    Returns
    -------
    List[Dict[str, Set[str]]]
        List with apointed backend and sensors for each MPI rank.
    """
    for host, ranks in hostNames.items():
        firstRank = ranks[0]
        firstRankDict = hostBackends[firstRank]
        for rank in ranks[1:]:
            firstRankDict = _mergeDicts(firstRankDict, hostBackends[rank])
            hostBackends[rank] = {}

        hostBackends[firstRank] = firstRankDict
    return hostBackends


def _mergeDicts(
    dict1: Dict[str, Set[str]], dict2: Dict[str, Set[str]]
) -> Dict[str, Set[str]]:
    for key, value in dict2.items():
        if key in dict1:
            dict1[key] |= value
        else:
            dict1[key] = value

    return dict1

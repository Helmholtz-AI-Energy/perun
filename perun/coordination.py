"""Coordination module."""
import platform
from typing import Dict, List, Optional, Set, Tuple

from perun import Comm, log
from perun.backend import Backend

_cached_sensor_config: Optional[Tuple[Dict, List]] = None


def getHostRankDict(comm: Comm) -> Dict[str, List[int]]:
    """Return a dictionary with all the host names with each MPI rank in them.

    Args:
        comm (Comm): MPI Communicator

    Returns:
        Dict[str, List[int]]: Dictionary with key hostnames and mpi ranks as values.
    """
    hostname = platform.node()
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
    comm: Comm, backends: List[Backend]
) -> Tuple[Dict[str, List[int]], List[Dict[str, Set[str]]]]:
    """Gather available sensor information from every MPI rank and assign/unassign sensors to each rank to avoid over sampling.

    Args:
        comm (Comm): MPI Communicator
        backends (List[Backend]): List of available backends in the current rank.

    Returns:
        Tuple[Dict[str, List[int]], List[Dict[str, Set[str]]]]: Global rank and sensor configuration objects.
    """
    visibleSensorsByBackend: Dict[str, Set[str]] = {
        backend.name: backend.visibleSensors() for backend in backends
    }
    log.debug(f"Rank {comm.Get_rank()} : Visible devices {visibleSensorsByBackend}")
    globalVisibleSensorsByBackend = comm.allgather(visibleSensorsByBackend)
    globalHostRanks = getHostRankDict(comm)

    globalSensorConfig = assignSensors(globalVisibleSensorsByBackend, globalHostRanks)
    return (
        globalHostRanks,
        globalSensorConfig,
    )


def getLocalSensorRankConfiguration(
    comm: Comm, backends: List[Backend]
) -> Tuple[List[int], Dict[str, Set[str]]]:
    """Obtain local sensor configuration.

    Args:
        comm (Comm): MPI Communicator
        backends (List[Backend]): List of availbale backends in the current ranks.

    Returns:
        Tuple[List[int], Dict[str, Set[str]]]: Local rank and sensor configuration
    """
    global _cached_sensor_config
    if _cached_sensor_config is None:
        globalHostRanks, globalSensorConfig = getGlobalSensorRankConfiguration(
            comm, backends
        )
        _cached_sensor_config = (globalHostRanks, globalSensorConfig)
    else:
        globalHostRanks, globalSensorConfig = _cached_sensor_config

    return globalHostRanks[platform.node()], globalSensorConfig[comm.Get_rank()]


def assignSensors(
    hostBackends: List[Dict[str, Set[str]]], hostNames: Dict[str, List[int]]
) -> List[Dict[str, Set[str]]]:
    """Assign found devices to the lowest rank in each host.

    Args:
        hostSensors (List[Set[str]]): List with lenght of the mpi world size, with each index containing the devices of each rank.
        hostNames (List[str]): Hostname of the mpi rank at the index.

    Returns:
        List[Set[str]]: New list with the devices assiged to each rank.
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

"""Coordination module."""

from typing import List, Set


def assignSensors(hostSensors: List[Set[str]], hostNames: List[str]) -> List[Set[str]]:
    """Assign found devices to the lowest rank in each host.

    Args:
        hostSensors (List[Set[str]]): List with lenght of the mpi world size, with each index containing the devices of each rank.
        hostNames (List[str]): Hostname of the mpi rank at the index.

    Returns:
        List[Set[str]]: New list with the devices assiged to each rank.
    """
    previousHosts = {}
    for index, (name, devices) in enumerate(zip(hostNames, hostSensors)):
        if name not in previousHosts:
            previousHosts[name] = index
        else:
            prevIndex = previousHosts[name]
            hostSensors[prevIndex] |= devices
            hostSensors[index] = set()
    return hostSensors

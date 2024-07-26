import random
from unittest.mock import MagicMock

from hypothesis import given
from hypothesis import strategies as st

from perun.comm import Comm
from perun.coordination import assignSensors, getHostRankDict


@given(
    hostnames=st.lists(
        st.tuples(st.text(), st.integers(min_value=1, max_value=5)), min_size=1
    ),
    available_sensors=st.dictionaries(st.text(), st.tuples(st.text(), st.text())),
)
def test_assignSensors(hostnames, available_sensors):
    # First test getHostRankDict
    hostnames_list = []
    for hostname, n in hostnames:
        hostnames_list.extend([hostname] * n)

    world_size = len(hostnames_list)
    comm = MagicMock(spec=Comm)
    comm.Get_rank = MagicMock(return_value=random.randint(0, world_size - 1))
    comm.Get_size = MagicMock(return_value=world_size)
    comm.allgather = MagicMock(
        return_value=[(hostnames_list[rank], rank) for rank in range(world_size)]
    )

    hostRankDict_result = getHostRankDict(comm, hostnames_list[comm.Get_rank()])

    assert isinstance(hostRankDict_result, dict)

    assigned_ranks = set()
    for key, value in hostRankDict_result.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        assert all(isinstance(rank, int) for rank in value)
        # Ensure that the ranks are unique across all hostnames, and are within the world size
        for rank in value:
            assert rank not in assigned_ranks
            assigned_ranks.add(rank)
            assert rank < world_size
            assert rank >= 0

    comm.Get_rank.assert_called()
    comm.allgather.assert_called()

    g_available_sensors = [available_sensors for _ in range(world_size)]

    assignedSensors_result = assignSensors(hostRankDict_result, g_available_sensors)
    assert isinstance(assignedSensors_result, list)
    assert len(assignedSensors_result) == world_size

    # Ensure that only the first rank of each host has sensors assigned
    for hostname, ranks in hostRankDict_result.items():
        for rank in ranks:
            if rank == min(ranks):
                assert assignedSensors_result[rank] == available_sensors
            else:
                assert assignedSensors_result[rank] == {}

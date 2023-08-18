from typing import Any, Dict, List, Set

import numpy as np

from perun.coordination import assignSensors

# from pytest import MonkeyPatch


def compareNestedListDictSet(
    l1: List[Dict[str, Set[Any]]], l2: List[Dict[str, Set[Any]]]
) -> bool:
    if len(l1) != len(l2):
        return False
    for nl1, nl2 in zip(l1, l2):
        if len(nl1) != len(nl2):
            return False
        for key1 in nl1.keys():
            if key1 not in nl2:
                return False

            if not np.all([e1 in nl1[key1] for e1 in nl2[key1]]):
                return False
    return True


def test_assignSensors():
    # Test single node
    # Input
    hosts = {"host0": [0]}
    devices = [{"b": {"s1", "s2", "s3"}}]

    result = devices
    output = assignSensors(devices, hosts)
    assert compareNestedListDictSet(result, output)

    # Test single node with multiple ranks, equal devices
    hosts = {"host0": [0, 1]}
    devices = [{"b": {"s1", "s2", "s3"}}, {"b": {"s1", "s2", "s3"}}]

    result = [{"b": {"s1", "s2", "s3"}}, {}]
    output = assignSensors(devices, hosts)
    assert compareNestedListDictSet(output, result)

    # Test single node with multiple ranks, different devices devices
    hosts = {"host0": [0, 1]}
    devices = [{"b": {"s1", "s2"}}, {"b": {"s2", "s3"}}]

    result = [{"b": {"s1", "s2", "s3"}}, {}]
    output = assignSensors(devices, hosts)
    assert compareNestedListDictSet(output, result)

    # Test single node, multiple ranks, different backends
    hosts = {"host0": [0, 1, 2]}
    devices = [
        {"b0": {"s1", "s2"}, "b1": {"s1", "s0"}},
        {"b0": {"s2", "s3"}},
        {"b1": {"s2"}},
    ]

    result = [{"b0": {"s1", "s2", "s3"}, "b1": {"s0", "s1", "s2"}}, {}, {}]
    output = assignSensors(devices, hosts)
    print(output)
    assert compareNestedListDictSet(output, result)

    # Test 2 nodes with single ranks, same devices
    hosts = {"host0": [0], "host1": [1]}
    devices = [{"b": {"s1", "s2"}}, {"b": {"s1", "s2"}}]

    result = [
        {
            "b": {
                "s1",
                "s2",
            }
        },
        {
            "b": {
                "s1",
                "s2",
            }
        },
    ]
    output = assignSensors(devices, hosts)
    assert compareNestedListDictSet(output, result)

    # Test 2 nodes with multiple ranks, different devices
    hosts = {"host0": [0, 1], "host1": [2, 3]}
    devices = [
        {"b0": {"s1", "s2"}, "b1": {"s1", "s0"}},
        {"b0": {"s2", "s3"}},
        {"b1": {"s1", "s0"}},
        {"b0": {"s2", "s3"}},
    ]

    result = [
        {"b0": {"s1", "s2", "s3"}, "b1": {"s1", "s0"}},
        {},
        {"b0": {"s2", "s3"}, "b1": {"s0", "s1"}},
        {},
    ]

    output = assignSensors(devices, hosts)
    assert compareNestedListDictSet(output, result)


# def test_perunSubprocess(monkeypatch: MonkeyPatch, backends):
#     monkeypatch.setattr(target="perun.backend.backend", name="backends", )


import pytest
from typing import List, Any

from perun.perun import assignDevices
import numpy as np

def compareNestedList(l1: List[List[Any]], l2: List[List[Any]]) -> bool:
    if len(l1) != len(l2):
        return False
    for nl1, nl2 in zip(l1, l2):
        if len(nl1) != len(nl2):
            return False
        if not np.all([e1 in nl2 for e1 in nl2]):
            return False
    return True

def test_assignDevices():
    # Test single node
    # Input
    hosts = ["host0"]
    devices = [{"d0", "d1", "d2"}]

    result = devices
    output = assignDevices(devices, hosts)
    assert compareNestedList(result, output)

    # Test single node with multiple ranks, equal devices
    hosts = ["host0", "host0"]
    devices = [{ "d0", "d1", "d2" }, { "d0", "d1", "d2" }]

    result = [{ "d0", "d1", "d2" }, {  }]
    output = assignDevices(devices, hosts)
    assert compareNestedList(output, result)

    # Test single node with multiple ranks, different devices devices
    hosts = ["host0", "host0"]
    devices = [{ "d0", "d1", "d2" }, { "d1", "d2", "d3" }]

    result = [{ "d0", "d1", "d2", "d3" }, {  }]
    output = assignDevices(devices, hosts)
    assert compareNestedList(output, result)

    # Test 2 nodes with single ranks, different devices devices
    hosts = ["host0", "host1"]
    devices = [{ "d0", "d1", "d2" }, { "d0", "d1", "d2" }]

    result = [{ "d0", "d1", "d2" }, { "d0", "d1", "d2" }]
    output = assignDevices(devices, hosts)
    assert compareNestedList(output, result)

    # Test 2 nodes with single ranks, different devices devices
    hosts = ["host0", "host0", "host1", "host1"]
    devices = [{ "d0", "d1", "d2" }, { "d0", "d1", "d2" }, { "d0", "d1", "d2" }, { "d0", "d1", "d2" }]

    result = [{ "d0", "d1", "d2" }, {  }, { "d0", "d1", "d2" }, {  }]
    output = assignDevices(devices, hosts)
    assert compareNestedList(output, result)

@pyte
def backends

def test_perunSubprocess()

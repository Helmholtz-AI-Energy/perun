"""IO Json module."""

import json

from perun.data_model.data import DataNode
from perun.io.util import NumpyEncoder


def exportJson(dataNode: DataNode) -> str:
    """Export DataNode to json.

    :param dataNode: DataNode
    :type dataNode: DataNode
    :return: Json string of data node.
    :rtype: str
    """
    dataDict = dataNode.toDict(True)
    return json.dumps(dataDict, cls=NumpyEncoder)


def importJson(jsonString: str) -> DataNode:
    """Create DataNode from JSON string."""
    return DataNode.fromDict(json.loads(jsonString))

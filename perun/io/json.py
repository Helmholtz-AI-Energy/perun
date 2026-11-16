"""IO Json module."""

import json

from perun.data_model.data import DataNode
from perun.io.util import NumpyEncoder


def exportJson(dataNode: DataNode) -> str:
    """Export DataNode to json.

    Parameters
    ----------
    dataNode : DataNode
        DataNode to export.

    Returns
    -------
    str
        Json string of data node.
    """
    dataDict = dataNode.toDict(True)
    return json.dumps(dataDict, cls=NumpyEncoder)


def importJson(jsonString: str) -> DataNode:
    """Create DataNode from JSON string.

    Parameters
    ----------
    jsonString : str
        Json string of a data node.

    Returns
    -------
    DataNode
        Imported DataNode.
    """
    return DataNode.fromDict(json.loads(jsonString))

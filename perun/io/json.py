"""IO Json module."""

import json

import numpy as np

from perun.data_model.data import DataNode


class NumpyEncoder(json.JSONEncoder):
    """Json Numpy object encoder."""

    def default(self, obj):
        """Encode obj to json or to a supported format.

        :param obj: Object to encode.
        :type obj: _type_
        :return: Encoded obj.
        :rtype: _type_
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.dtype):
            return str(obj)
        else:
            return super(NumpyEncoder, self).default(obj)


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

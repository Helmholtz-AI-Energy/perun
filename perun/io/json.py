"""IO Json module."""
import json
from typing import Optional

import numpy as np

from perun.data_model.data import DataNode


class NumpyEncoder(json.JSONEncoder):
    """Json Numpy object encoder."""

    def default(self, obj):
        """Transform numpy objects.

        Args:
            obj (_type_): Numpy object
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


def exportJson(
    dataNode: DataNode, depth: Optional[int] = None, include_raw: bool = False
) -> str:
    """Export DataNode to json.

    Args:
        dataNode (DataNode): DataNode
        depth (Optional[int], optional): If specified, export only the first 'depth' levels of the DataNode tree. Defaults to None.
        include_raw (bool, optional): If raw data should be included. Defaults to False.

    Returns:
        str: json string from dataNode
    """
    dataDict = dataNode.toDict(depth, include_raw)
    return json.dumps(dataDict, indent=4, cls=NumpyEncoder)


def importJson(jsonString: str) -> DataNode:
    """Create DataNode from JSON string."""
    return DataNode.fromDict(json.loads(jsonString))

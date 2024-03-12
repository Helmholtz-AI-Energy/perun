"""IO Pickle module."""

import pickle

from perun.data_model.data import DataNode


def exportPickle(dataNode: DataNode) -> bytes:
    """Export data node to pickle file.

    Parameters
    ----------
    dataNode : DataNode
        Data Node

    Returns
    -------
    bytes
        Binary data to write to file.
    """
    return pickle.dumps(dataNode)


def importPickle(pickleData: bytes) -> DataNode:
    """Import DataNode from pickled data file.

    Parameters
    ----------
    pickleData : bytes
        Binary Data

    Returns
    -------
    DataNode
        DataNode
    """
    return pickle.loads(pickleData)

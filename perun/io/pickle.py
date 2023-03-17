"""IO Pickle module."""
import pickle

from perun.data_model.data import DataNode


def exportPickle(dataNode: DataNode) -> bytes:
    """Pickle data node.

    Args:
        dataNode (DataNode): DataNode to be pickled.

    Returns:
        bytes: Pickled DataNode
    """
    return pickle.dumps(dataNode)


def importPickle(pickleData: bytes) -> DataNode:
    """Unpickle DataNode.

    Args:
        pickleData (bytes): Pickled DataNode

    Returns:
        DataNode: Unpickled DataNode
    """
    return pickle.loads(pickleData)

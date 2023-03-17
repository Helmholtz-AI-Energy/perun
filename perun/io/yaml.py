"""IO Yaml module."""
from typing import Optional

from perun.data_model.data import DataNode

# import yaml


def exportYaml(
    dataNode: DataNode, depth: Optional[int] = None, include_raw: bool = False
) -> str:
    """Export DataNode to yaml format.

    Args:
        dataNode (DataNode): DataNode
        depth (Optional[int], optional): If specified, export only the first 'depth' levels of the DataNode tree. Defaults to None.
        include_raw (bool, optional): If raw data should be included. Defaults to False.

    Returns:
        str: json string from dataNode
    """
    raise NotImplementedError("Featured is in development.")


def importYaml(yamlStr: str) -> DataNode:
    """Create DataNode from YAML object.

    Args:
        yamlStr (str): YAML string

    Returns:
        DataNode: DataNode
    """
    raise NotImplementedError("Feature not implemented yet.")

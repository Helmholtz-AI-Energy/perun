"""Comm module."""
from typing import Any, List, Optional

from perun import log


class Comm:
    """Wrapper around MPI COMM_WORLD. Does nothing if MPI is not initialized."""

    def __init__(self):
        """Initialize MPI Communicator if availablel."""
        self._enabled = False
        self._rank = 0
        self._size = 1
        try:
            from mpi4py import MPI

            if MPI.COMM_WORLD.Get_size() >= 1:
                self._comm = MPI.COMM_WORLD
                self._enabled = True

        except ImportError as e:
            log.warning("Missing mpi4py, multi-node monitoring disabled")
            log.warning(e)

    def Get_rank(self) -> int:
        """Return MPI rank.

        Returns:
            int: MPI Rank
        """
        return self._comm.Get_rank() if self._enabled else self._rank

    def Get_size(self) -> int:
        """Return MPI world size.

        Returns:
            int: MPI world size
        """
        return self._comm.Get_size() if self._enabled else self._size

    def gather(self, obj: Any, root: int = 0) -> Optional[List[Any]]:
        """MPI gather operation at selected rank.

        Args:
            obj (Any): Object to be gathererd.
            root (int, optional): Rank to gather information at. Defaults to 0.

        Returns:
            Optional[List[Any]]: List with objects from all the ranks.
        """
        return self._comm.gather(obj, root=root) if self._enabled else [obj]

    def allgather(self, obj: Any) -> List[Any]:
        """MPI allgather operation."""
        if self._enabled:
            return self._comm.allgather(obj)
        else:
            return [obj]

    def bcast(self, obj: Any, root: int = 0) -> Any:
        """MPI broadcast operation."""
        if self._enabled:
            return self._comm.bcast(obj, root)
        else:
            return obj

    def barrier(self):
        """MPI barrier operation."""
        if self._enabled:
            self._comm.barrier()

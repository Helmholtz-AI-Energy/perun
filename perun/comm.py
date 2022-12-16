from typing import Any, List

from perun import log


class Comm:
    def __init__(self):
        self._enabled = False
        self._rank = 0
        self._size = 1
        try:
            from mpi4py import MPI

            if MPI.COMM_WORLD.Get_size() >= 1:
                self._comm = MPI.COMM_WORLD
                self._enabled = True

        except ImportError as e:
            log.warn("Missing mpi4py, multi-node monitoring disabled")
            log.warn(e)

    def Get_rank(self) -> int:
        return self._comm.Get_rank() if self._enabled else self._rank

    def Get_size(self) -> int:
        return self._comm.Get_size() if self._enabled else self._size

    def allgather(self, obj: Any) -> List[Any]:
        if self._enabled:
            return self._comm.allgather(obj)
        else:
            return [obj]

    def bcast(self, obj: Any, root: int = 0) -> Any:
        if self._enabled:
            return self._comm.bcast(obj, root)
        else:
            return obj

    def barrier(self):
        if self._enabled:
            self._comm.barrier()

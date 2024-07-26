"""Comm module."""

import logging
import sys
import time
from typing import Any, List, Optional

log = logging.getLogger("perun")


class Comm:
    """Wrapper around MPI COMM_WORLD. Does nothing if MPI is not initialized."""

    def __init__(self):
        """Initialize MPI Communicator if availablel."""
        self._enabled = False
        self._initialized = False
        self._rank = 0
        self._size = 1
        try:
            import mpi4py

            mpi4py.rc.initialize = False
            mpi4py.rc.finalize = True

            from mpi4py import MPI

            self._MPI = MPI
            self._enabled = True

        except ImportError as e:
            log.info("Missing mpi4py, multi-node monitoring disabled")
            log.info(e)

    def _mpi_init(self):
        log.debug("Initializing MPI")
        if not self._MPI.Is_initialized():
            self._MPI.Init()
        self._comm = self._MPI.COMM_WORLD
        self._rank = self._comm.Get_rank()
        self._size = self._comm.Get_size()
        self._initialized = True
        log.info(f"MPI initialized: rank={self._rank}, size={self._size}")
        if self._size == 1:
            log.info("Single node monitoring mode")

    def Get_rank(self) -> int:
        """Get local MPI rank.

        Returns
        -------
        int
            MPI Rank
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            return self._comm.Get_rank()
        else:
            return self._rank

    def Get_size(self) -> int:
        """MPI World size.

        Returns
        -------
        int
            World Size
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            return self._comm.Get_size()
        else:
            return self._size

    def gather(self, obj: Any, root: int = 0) -> Optional[List[Any]]:
        """MPI gather operation.

        Parameters
        ----------
        obj : Any
            Object to be gathered.
        root : int, optional
            Reciever rank, by default 0

        Returns
        -------
        Optional[List[Any]]
            List with the gathered objects.
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            return self._comm.gather(obj, root=root)
        else:
            return [obj]

    def allgather(self, obj: Any) -> List[Any]:
        """MPI allgather operation.

        Parameters
        ----------
        obj : Any
            Object to be gathered.

        Returns
        -------
        List[Any]
            List with the gathered objects.
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            return self._comm.allgather(obj)
        else:
            return [obj]

    def bcast(self, obj: Any, root: int = 0) -> Any:
        """MPI broadcast operation.

        Parameters
        ----------
        obj : Any
            Object to be broadcasted.
        root : int, optional
            Sender rank, by default 0

        Returns
        -------
        Any
            Broadcasted object.
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            return self._comm.bcast(obj, root)
        else:
            return obj

    def barrier(self):
        """MPI barrier operation."""
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            self._comm.barrier()

    def Abort(self, errorcode: int):
        """MPI Abort operation."""
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            self._comm.Abort(errorcode=errorcode)
        else:
            sys.exit(1)

    def gather_from_ranks(
        self, obj: Any, ranks: List[int], root: int = 0
    ) -> Optional[List[Any]]:
        """Collect python objects from specific ranks at the determined root.

        Parameters
        ----------
        obj : Any
            Object to be collected.
        ranks : List[int]
            List of ranks that need to send the object.
        root : int, optional
            Reciever rank, by default 0

        Returns
        -------
        Optional[List[Any]]
            List with the gathered objects.
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            result = None
            if self.Get_rank() != root:
                self._comm.send(obj, root)
            else:
                result = []
                for rank in ranks:
                    if self.Get_rank() != rank:
                        result.append(self._comm.recv(source=rank))
                    else:
                        result.append(obj)

            return result
        else:
            return [obj]

    def check_available_ranks(self) -> List[int]:
        """Return an array with all the ranks that are capable of responding to a single send/recv.

        Returns
        -------
        List[int]
            List with responsive MPI ranks.
        """
        if self._enabled:
            if not self._initialized:
                self._mpi_init()
            rank = self._comm.Get_rank()
            size = self._comm.Get_size()

            # Create a list to store available ranks
            available_ranks = []

            # Start time for the timeout mechanism
            start_time = time.time()

            # Non-blocking receive requests list
            requests = []

            for target_rank in range(size):
                if target_rank != rank:
                    self._comm.isend(rank, dest=target_rank, tag=0)

            # Initiate non-blocking receive requests from all other ranks
            for target_rank in range(size):
                if target_rank != rank:  # Skip sending to self
                    req = self._comm.irecv(source=target_rank, tag=0)
                    requests.append((target_rank, req))

            # Check for available ranks while handling timeouts
            while time.time() - start_time < 5:  # 5 seconds timeout for demonstration
                for target_rank, req in requests:
                    if target_rank not in available_ranks:
                        if req.Test():  # Check if a request has received a message
                            available_ranks.append(
                                target_rank
                            )  # Add the rank to available list

                if len(available_ranks) == size - 1:  # All ranks are available
                    break

                # Sleep for a short duration before checking again
                time.sleep(0.1)

            # Cancel all remaining requests to prevent potential deadlocks
            for target_rank, req in requests:
                if target_rank not in available_ranks:
                    req.Cancel()

            available_ranks.append(rank)
            sorted_available_ranks = sorted(available_ranks)
            return sorted_available_ranks
        else:
            return [0]

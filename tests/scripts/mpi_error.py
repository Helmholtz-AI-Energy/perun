import time

from mpi4py import MPI

comm = MPI.COMM_WORLD
files = ["tests/scripts/exists.txt", "does-not-exist.txt"]

rank = comm.Get_rank()

print(f"R{rank}: Hello world!")
time.sleep(5)

print(f"R{rank}: Reading file")
with open(files[rank % 2], "r") as file:
    lines = file.readlines()
    for line in lines:
        print(line)

print(f"R{rank}: Waiting for other ranks")
time.sleep(5)
comm.barrier()
print(f"R{rank}: Exit")

#!/bin/bash
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

export MASTER_PORT=$(expr 2950 + $(echo -n $SLURM_JOBID | tail -c 4))
export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export HSA_FORCE_FINE_GRAIN_PCIE=1


srun bash -lc 'torchrun \
                --nnodes=$SLURM_JOB_NUM_NODES --nproc-per-node gpu \
                --rdzv_backend=c10d --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT \
                 ddp.py'

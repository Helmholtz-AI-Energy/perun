# Torchrun example

In order to make this work, the perun context has to be manually activated only in one process per node. This can be achived using the dist object to get information about the global context, and by chainging **app_name** argument, in order to ensure that no files are not being writen at the same time.

## How to run

**Single node example**

```console
sbatch --gres=gpu:4 --tasks-per-node 1 --gpus-per-task 4 --cpus-per-task 12 -N 1 -t 20:00 srun_script.sh
```

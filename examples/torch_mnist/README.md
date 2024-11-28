# Torch MNIST Example

This directory contains everything to you need to start using **perun** in your workflows. As an example, we are using the [torch](https://pytorch.org/) package to train a neural network to recognize the handwritten digits using the MNIST dataset.

## Setup

It is recommended that you create a new environment with any new project using the *venv* package

```console
python -m venv venv/perun-example
source venv/perun-example/bin/activate
```

or with *conda*

```console
conda create --name perun-example
conda activate perun-example
```

Once your new enviornment is ready, you can install the dependencies for the example.

```console
pip install torch perun[mpi,nvidia]
```

This includes **perun** and the scripts dependencies. The the root of the project includes a minimal configuration file example.perun.ini*, with some basic options. More details on the configuration options can be found [in the docs](https://perun.readthedocs.io/en/latest/configuration.html).

To make sure **perun** was installed properly and that it has access to some hardware sensors, run the command

```console
perun sensors
```

## Monitoring

Now everything is ready to start getting data. To get monitor your script a single time, simply run:

```console
perun monitor torch_mnist.py
```

After the script finishes running, a folder *perun_results* will be created containing the consumption report of your application as a text file, including the all the raw data saved in an hdf5 file.

To explored the contents of the hdf5 file, we recomed the **h5py** library or the [myHDF5](https://myhdf5.hdfgroup.org) website.

The text report from running the MNIST example should look like this:

```text
PERUN REPORT

App name: torch_mnist
First run: 2023-08-22T17:44:34.927402
Last run: 2023-08-22T17:44:34.927402


RUN ID: 2023-08-22T17:44:34.927402

|   Round # | Host                | RUNTIME   | ENERGY    | CPU_POWER   | CPU_UTIL   | GPU_POWER   | GPU_MEM   | DRAM_POWER   | MEM_UTIL   |
|----------:|:--------------------|:----------|:----------|:------------|:-----------|:------------|:----------|:-------------|:-----------|
|         0 | hkn0402.localdomain | 61.954 s  | 28.440 kJ | 203.619 W   | 0.867 %    | 232.448 W   | 4.037 GB  | 22.923 W     | 0.033 %    |
|         0 | All                 | 61.954 s  | 28.440 kJ | 203.619 W   | 0.867 %    | 232.448 W   | 4.037 GB  | 22.923 W     | 0.033 %    |

Monitored Functions

|   Round # | Function    |   Avg Calls / Rank | Avg Runtime    | Avg Power        | Avg CPU Util   | Avg GPU Mem Util   |
|----------:|:------------|-------------------:|:---------------|:-----------------|:---------------|:-------------------|
|         0 | train       |                  1 | 50.390±0.000 s | 456.993±0.000 W  | 0.869±0.000 %  | 2.731±0.000 %      |
|         0 | train_epoch |                  5 | 8.980±1.055 s  | 433.082±11.012 W | 0.874±0.007 %  | 2.746±0.148 %      |
|         0 | test        |                  5 | 1.098±0.003 s  | 274.947±83.746 W | 0.804±0.030 %  | 2.808±0.025 %      |

The application has been run 1 times. In total, it has used 0.012 kWh, released a total of 0.005 kgCO2e into the atmosphere, and you paid 0.00 € in electricity for it.
```

The results display data about the functions *train*, *test_epoch* and *test*. Those functions were specialy marked using the ```@monitor()``` decorator.

```python
@monitor()
def train(args, model, device, train_loader, test_loader, optimizer, scheduler):
    for epoch in range(1, args.epochs + 1):
        train_epoch(args, model, device, train_loader, optimizer, epoch)
        test(model, device, test_loader)
        scheduler.step()
```

## Benchmarking

If you need to run your code multiple times to gather statistics, perun includes an option called ```--rounds```. The application will be run multiple times, with each run added to similar tables as the one generated for a single run.


```console
perun monitor --rounds 5 torch_mnist.py
```

```text
PERUN REPORT

App name: torch_mnist
First run: 2023-08-22T17:44:34.927402
Last run: 2023-08-22T17:45:46.992693


RUN ID: 2023-08-22T17:45:46.992693

|   Round # | Host                | RUNTIME   | ENERGY    | CPU_POWER   | CPU_UTIL   | GPU_POWER   | GPU_MEM   | DRAM_POWER   | MEM_UTIL   |
|----------:|:--------------------|:----------|:----------|:------------|:-----------|:------------|:----------|:-------------|:-----------|
|         0 | hkn0402.localdomain | 52.988 s  | 24.379 kJ | 202.854 W   | 0.865 %    | 234.184 W   | 4.281 GB  | 22.858 W     | 0.034 %    |
|         0 | All                 | 52.988 s  | 24.379 kJ | 202.854 W   | 0.865 %    | 234.184 W   | 4.281 GB  | 22.858 W     | 0.034 %    |
|         1 | hkn0402.localdomain | 48.401 s  | 22.319 kJ | 203.366 W   | 0.886 %    | 234.821 W   | 4.513 GB  | 22.798 W     | 0.034 %    |
|         1 | All                 | 48.401 s  | 22.319 kJ | 203.366 W   | 0.886 %    | 234.821 W   | 4.513 GB  | 22.798 W     | 0.034 %    |
|         2 | hkn0402.localdomain | 48.258 s  | 22.248 kJ | 203.339 W   | 0.884 %    | 234.720 W   | 4.513 GB  | 22.850 W     | 0.034 %    |
|         2 | All                 | 48.258 s  | 22.248 kJ | 203.339 W   | 0.884 %    | 234.720 W   | 4.513 GB  | 22.850 W     | 0.034 %    |
|         3 | hkn0402.localdomain | 48.537 s  | 22.393 kJ | 203.269 W   | 0.884 %    | 234.984 W   | 4.513 GB  | 22.968 W     | 0.034 %    |
|         3 | All                 | 48.537 s  | 22.393 kJ | 203.269 W   | 0.884 %    | 234.984 W   | 4.513 GB  | 22.968 W     | 0.034 %    |
|         4 | hkn0402.localdomain | 48.416 s  | 22.323 kJ | 203.408 W   | 0.888 %    | 234.626 W   | 4.513 GB  | 22.928 W     | 0.034 %    |
|         4 | All                 | 48.416 s  | 22.323 kJ | 203.408 W   | 0.888 %    | 234.626 W   | 4.513 GB  | 22.928 W     | 0.034 %    |

Monitored Functions

|   Round # | Function    |   Avg Calls / Rank | Avg Runtime    | Avg Power        | Avg CPU Util   | Avg GPU Mem Util   |
|----------:|:------------|-------------------:|:---------------|:-----------------|:---------------|:-------------------|
|         0 | train       |                  1 | 50.169±0.000 s | 458.380±0.000 W  | 0.875±0.000 %  | 2.727±0.000 %      |
|         0 | train_epoch |                  5 | 8.930±0.903 s  | 439.707±12.743 W | 0.875±0.008 %  | 2.743±0.154 %      |
|         0 | test        |                  5 | 1.103±0.004 s  | 232.750±1.219 W  | 0.805±0.030 %  | 2.809±0.023 %      |
|         1 | train       |                  1 | 48.354±0.000 s | 453.376±0.000 W  | 0.886±0.000 %  | 2.820±0.000 %      |
|         1 | train_epoch |                  5 | 8.556±0.008 s  | 428.418±11.199 W | 0.890±0.018 %  | 2.820±0.000 %      |
|         1 | test        |                  5 | 1.115±0.002 s  | 272.918±80.330 W | 0.798±0.018 %  | 2.820±0.000 %      |
|         2 | train       |                  1 | 48.210±0.000 s | 453.867±0.000 W  | 0.884±0.000 %  | 2.820±0.000 %      |
|         2 | train_epoch |                  5 | 8.525±0.022 s  | 423.647±1.049 W  | 0.888±0.013 %  | 2.820±0.000 %      |
|         2 | test        |                  5 | 1.117±0.005 s  | 312.983±97.688 W | 0.806±0.012 %  | 2.820±0.000 %      |
|         3 | train       |                  1 | 48.486±0.000 s | 452.940±0.000 W  | 0.884±0.000 %  | 2.820±0.000 %      |
|         3 | train_epoch |                  5 | 8.577±0.012 s  | 433.627±13.812 W | 0.888±0.017 %  | 2.820±0.000 %      |
|         3 | test        |                  5 | 1.120±0.003 s  | 233.973±3.516 W  | 0.789±0.022 %  | 2.820±0.000 %      |
|         4 | train       |                  1 | 48.367±0.000 s | 453.256±0.000 W  | 0.888±0.000 %  | 2.820±0.000 %      |
|         4 | train_epoch |                  5 | 8.555±0.011 s  | 433.582±12.606 W | 0.899±0.029 %  | 2.820±0.000 %      |
|         4 | test        |                  5 | 1.118±0.002 s  | 233.367±2.238 W  | 0.818±0.045 %  | 2.820±0.000 %      |

The application has been run 2 times. In total, it has used 0.062 kWh, released a total of 0.026 kgCO2e into the atmosphere, and you paid 0.02 € in electricity for it.
```

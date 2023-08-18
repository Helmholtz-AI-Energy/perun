<div align="center">
  <img src="https://raw.githubusercontent.com/Helmholtz-AI-Energy/perun/main/docs/images/full_logo.svg">
</div>

&nbsp;
&nbsp;

[![fair-software.eu](https://img.shields.io/badge/fair--software.eu-%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F-green)](https://fair-software.eu)
[![OpenSSF Best Practices](https://bestpractices.coreinfrastructure.org/projects/7253/badge)](https://bestpractices.coreinfrastructure.org/projects/7253)
[![DOI](https://zenodo.org/badge/523363424.svg)](https://zenodo.org/badge/latestdoi/523363424)
![PyPI](https://img.shields.io/pypi/v/perun)
![PyPI - Downloads](https://img.shields.io/pypi/dm/perun)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Documentation Status](https://readthedocs.org/projects/perun/badge/?version=latest)](https://perun.readthedocs.io/en/latest/?badge=latest)

perun is a Python package that calculates the energy consumption of Python scripts by sampling usage statistics from Intel RAPL, Nvidia-NVML, and psutil. It can handle MPI applications, gather data from hundreds of nodes, and accumulate it efficiently. perun can be used as a command-line tool or as a function decorator in Python scripts.

Check out the [docs](https://perun.readthedocs.io/en/latest/)!

## Key Features

 - Measures energy consumption of Python scripts using Intel RAPL, Nvidia-NVML, and psutil
 - Handles MPI applications efficiently
 - Gathers data from hundreds of nodes and accumulates it efficiently
 - Monitor individual functions using decorators
 - Tracks energy usage of the application over multiple executions
 - Easy to benchmark applications and functions

## Installation

From PyPI:

```console
pip install perun
```

From Github:

```console
pip install git+https://github.com/Helmholtz-AI-Energy/perun
```

## Quick Start

### Command Line

To use perun as a command-line tool, run the monitor subcommand followed by the path to your Python script and its arguments:

```console
$ perun monitor path/to/your/script.py [args]
```

perun will output two files, and HDF5 style containing all the raw data that was gathered, and a text file with a summary of the results.


```text
PERUN REPORT

App name: finetune_qa_accelerate
First run: 2023-08-15T18:56:11.202060
Last run: 2023-08-17T13:29:29.969779


RUN ID: 2023-08-17T13:29:29.969779

|   Round # | Host                | RUNTIME   | ENERGY     | CPU_POWER   | CPU_UTIL   | GPU_POWER   | GPU_MEM    | DRAM_POWER   | MEM_UTIL   |
|----------:|:--------------------|:----------|:-----------|:------------|:-----------|:------------|:-----------|:-------------|:-----------|
|         0 | hkn0432.localdomain | 995.967 s | 960.506 kJ | 231.819 W   | 3.240 %    | 702.327 W   | 55.258 GB  | 29.315 W     | 0.062 %    |
|         0 | hkn0436.localdomain | 994.847 s | 960.469 kJ | 235.162 W   | 3.239 %    | 701.588 W   | 56.934 GB  | 27.830 W     | 0.061 %    |
|         0 | All                 | 995.967 s | 1.921 MJ   | 466.981 W   | 3.240 %    | 1.404 kW    | 112.192 GB | 57.145 W     | 0.061 %    |

The application has run been run 7 times. Throught its runtime, it has used 3.128 kWh, released a total of 1.307 kgCO2e into the atmosphere, and you paid 1.02 € in electricity for it.
```

Perun will keep track of the energy of your application over multiple runs.

### Function Monitoring

Using a function decorator, information can be calculated about the runtime, power draw and component utilization while the function is executing.

```python

import time
from perun import monitor

@monitor()
def main(n: int):
    time.sleep(n)
```

After running the script with ```perun monitor```, the text report will add information about the monitored functions.

```text
Monitored Functions

|   Round # | Function                    |   Avg Calls / Rank | Avg Runtime     | Avg Power        | Avg CPU Util   | Avg GPU Mem Util   |
|----------:|:----------------------------|-------------------:|:----------------|:-----------------|:---------------|:-------------------|
|         0 | main                        |                  1 | 993.323±0.587 s | 964.732±0.499 W  | 3.244±0.003 %  | 35.091±0.526 %     |
|         0 | prepare_train_features      |                 88 | 0.383±0.048 s   | 262.305±19.251 W | 4.541±0.320 %  | 3.937±0.013 %      |
|         0 | prepare_validation_features |                 11 | 0.372±0.079 s   | 272.161±19.404 W | 4.524±0.225 %  | 4.490±0.907 %      |
```

### MPI

Perun is compatible with MPI applications that make use of ```mpi4py```, and requires changes in the code or in the perun configuration. Simply replace the ```python``` command with ```perun monitor```.

```console
mpirun -n 8 perun monitor path/to/your/script.py
```

## Docs

To get more information, check out our [docs page](https://perun.readthedocs.io/en/latest/).

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
[![codecov](https://codecov.io/gh/Helmholtz-AI-Energy/perun/graph/badge.svg?token=9O6FSJ6I3G)](https://codecov.io/gh/Helmholtz-AI-Energy/perun)
[![](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Documentation Status](https://readthedocs.org/projects/perun/badge/?version=latest)](https://perun.readthedocs.io/en/latest/?badge=latest)

perun is a Python package that calculates the energy consumption of Python scripts by sampling usage statistics from your Intel, Nvidia or AMD hardware components. It can handle MPI applications, gather data from hundreds of nodes, and accumulate it efficiently. perun can be used as a command-line tool or as a function decorator in Python scripts.

Check out the [docs](https://perun.readthedocs.io/en/latest/) or a working [example](https://github.com/Helmholtz-AI-Energy/perun/blob/main/examples/torch_mnist/README.md)!

## Key Features

 - Measures energy consumption of Python scripts using Intel RAPL, ROCM-SMI, Nvidia-NVML, and psutil
 - Capable of handling MPI application, gathering data from hundreds of nodes efficiently
 - Monitor individual functions using decorators
 - Tracks energy usage of the application over multiple executions
 - Easy to benchmark applications and functions
 - Experimental!: Can monitor any non-distributed command line application

## Installation

From PyPI:

```console
pip install perun
```

> Extra dependencies like nvidia-smi, rocm-smi and mpi can be installed using pip as well:
```console
pip install perun[nvidia, rocm, mpi]
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

The application has been run 7 times. In total, it has used 3.128 kWh, released a total of 1.307 kgCO2e into the atmosphere, and you paid 1.02 € in electricity for it.
```

Perun will keep track of the energy of your application over multiple runs.

#### Binary support (experimental)

perun is capable of monitoring simple applications written in other languages, as long as they don't make use of MPI or are distributed over multiple computational nodes.

```console
$ perun monitor --binary path/to/your/executable [args]
```

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

To get more information, check out our [docs page](https://perun.readthedocs.io/en/latest/) or check the [examples](https://github.com/Helmholtz-AI-Energy/perun/tree/main/examples).

## Citing perun

If you found perun usefull, please consider citing the conference paper:

 * Gutiérrez Hermosillo Muriedas, J.P., Flügel, K., Debus, C., Obermaier, H., Streit, A., Götz, M.: perun: Benchmarking Energy Consumption of High-Performance Computing Applications. In: Cano, J., Dikaiakos, M.D., Papadopoulos, G.A., Pericàs, M., and Sakellariou, R. (eds.) Euro-Par 2023: Parallel Processing. pp. 17–31. Springer Nature Switzerland, Cham (2023). https://doi.org/10.1007/978-3-031-39698-4_2.


```bibtex
@InProceedings{10.1007/978-3-031-39698-4_2,
  author="Guti{\'e}rrez Hermosillo Muriedas, Juan Pedro
  and Fl{\"u}gel, Katharina
  and Debus, Charlotte
  and Obermaier, Holger
  and Streit, Achim
  and G{\"o}tz, Markus",
  editor="Cano, Jos{\'e}
  and Dikaiakos, Marios D.
  and Papadopoulos, George A.
  and Peric{\`a}s, Miquel
  and Sakellariou, Rizos",
  title="perun: Benchmarking Energy Consumption of High-Performance Computing Applications",
  booktitle="Euro-Par 2023: Parallel Processing",
  year="2023",
  publisher="Springer Nature Switzerland",
  address="Cham",
  pages="17--31",
  abstract="Looking closely at the Top500 list of high-performance computers (HPC) in the world, it becomes clear that computing power is not the only number that has been growing in the last three decades. The amount of power required to operate such massive computing machines has been steadily increasing, earning HPC users a higher than usual carbon footprint. While the problem is well known in academia, the exact energy requirements of hardware, software and how to optimize it are hard to quantify. To tackle this issue, we need tools to understand the software and its relationship with power consumption in today's high performance computers. With that in mind, we present perun, a Python package and command line interface to measure energy consumption based on hardware performance counters and selected physical measurement sensors. This enables accurate energy measurements on various scales of computing, from a single laptop to an MPI-distributed HPC application. We include an analysis of the discrepancies between these sensor readings and hardware performance counters, with particular focus on the power draw of the usually overlooked non-compute components such as memory. One of our major insights is their significant share of the total energy consumption. We have equally analyzed the runtime and energy overhead perun generates when monitoring common HPC applications, and found it to be minimal. Finally, an analysis on the accuracy of different measuring methodologies when applied at large scales is presented.",
  isbn="978-3-031-39698-4"
}
```

<div align="center">
  <img src="https://raw.githubusercontent.com/Helmholtz-AI-Energy/perun/main/docs/images/perun.svg">
</div>

&nbsp;
&nbsp;

[![fair-software.eu](https://img.shields.io/badge/fair--software.eu-%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8B%20%20%E2%97%8B%20%20%E2%97%8B-orange)](https://fair-software.eu)
![PyPI](https://img.shields.io/pypi/v/perun)
![PyPI - Downloads](https://img.shields.io/pypi/dm/perun)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Have you ever wondered how much energy is used when training your neural network on the MNIST dataset? Want to get scared because of impact you are having on the evironment while doing "valuable" research? Are you interested in knowing how much carbon you are burning playing with DALL-E just to get attention on twitter? If the thing that was missing from your machine learning workflow was existential dread, this is the correct package for you!

perun is python package that calculates the energy consumption of your python scripts by sampling usage statistics from Intel RAPL, Nvidia-NVML and *psutil*. Unlike other energy measuring applications out there, this is the only one capable of handling MPI applications, being capable of gathering data from 100s of nodes at the same time, and accumulating it efficiently. This is posible without adding any line of code into your existing application, and without meaningfully extending the runtime of your application.

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

Perun has two usage methods, either using the command line, or using function decorators.

### Command line

When using the command line, perun will output file containing runtime, energy and other information gathered while your script runs.

```console
$ perun monitor path/to/your/script.py [args]
$ cat perun_results/script_2023-03-23T12:10:48.627214.txt
PERUN REPORT

App name: script
Run ID: 2023-03-23T12:10:48.627214
RUNTIME: 0:00:06.333626 s
CPU_UTIL: 64.825 %
MEM_UTIL: 0.563 %
NET_READ: 1.401 kB
NET_WRITE: 1.292 kB
DISK_READ: 174.633 MB
DISK_WRITE: 88.000 kB
```

### Decorator

Perun can also monitor individual functions using a decorator:

```python
import time
from perun.decorator import monitor

@monitor()
def your_sleep_function(n: int):
    time.sleep(n)
```

And then running your script like always:

```console
python path/to/your/script.py
```

> :exclamation: Each time the function is run, perun will output a new report from the function.

### MPI

If your python application uses mpi4py, you don't need to change anything. Perun is able to handle MPI applications, and will gather statistics in all the utilized nodes.

```console
mpirun -n 8 perun monitor path/to/your/script.py
```

or

```
mpirun -n 8 python path/to/your/script.py
```

## Usage

### Subcommands

Perun subcommands have some shared options that are typed before the subcommands.

```console
Usage: perun [OPTIONS] COMMAND [ARGS]...

  Perun: Energy measuring and reporting tool.

Options:
  --version                       Show the version and exit.
  -c, --configuration FILE        Path to configuration file
  -n, --app_name TEXT             Name of the monitored application. The name
                                  is used to distinguish between multiple
                                  applications in the same directory. If left
                                  empty, the filename will be  used.
  -i, --run_id TEXT               Unique id of the latest run of the
                                  application. If left empty, perun will use
                                  the SLURM job id, or the current date.
  --format [text|json|hdf5|pickle|csv|bench]
                                  Report format.
  --data_out DIRECTORY            Where to save the output files, defaults to
                                  the current working directory.
  --raw                           Use the flag '--raw' if you need access to
                                  all the raw data collected by perun. The
                                  output will be saved on an hdf5 file on the
                                  perun data output location.
  --sampling_rate FLOAT           Sampling rate in seconds.
  --pue FLOAT                     Data center Power Usage Efficiency.
  --emissions_factor FLOAT        Emissions factor at compute resource
                                  location.
  --price_factor FLOAT            Electricity price factor at compute resource
                                  location.
  --bench                         Activate benchmarking mode.
  --bench_rounds INTEGER          Number of rounds per function/app.
  --bench_warmup_rounds INTEGER   Number of warmup rounds per function/app.
  -l, --log_lvl [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                  Loggging level
  --help                          Show this message and exit.

Commands:
  export    Export existing perun output file to another format.
  monitor   Gather power consumption from hardware devices while SCRIPT...
  sensors   Print sensors assigned to each rank by perun.
  showconf  Print current perun configuration in INI format.
```

### monitor

Monitor energy usage of a python script.

```console
Usage: perun monitor [OPTIONS] SCRIPT [SCRIPT_ARGS]...

  Gather power consumption from hardware devices while SCRIPT [SCRIPT_ARGS] is
  running.

  SCRIPT is a path to the python script to monitor, run with arguments
  SCRIPT_ARGS.

Options:
  --help  Show this message and exit.
```

### sensors

Print available monitoring backends and each available sensors for each MPI rank.

```console
Usage: perun sensors [OPTIONS]

  Print sensors assigned to each rank by perun.

Options:
  --help  Show this message and exit.
```

### export

Export an existing perun output file to another format.

```console
Usage: perun export [OPTIONS] INPUT_FILE OUTPUT_PATH
                    {text|json|hdf5|pickle|csv|bench}

  Export existing perun output file to another format.

Options:
  --help  Show this message and exit.
```

### showconf

Prints the current option configurations based on the global, local configurations files and command line options.

```console
Usage: perun showconf [OPTIONS]

  Print current perun configuration in INI format.

Options:
  --default  Print default configuration
  --help     Show this message and exit.
```

## Configuration

There are multiple ways to configure perun, with a different level of priorities.

- CMD Line options and Env Variables

  The highest priority is given to command line options and environmental variables. The options are shown in the command line section. The options can also be passed as environmental variables by adding the prefix 'PERUN' to them. Ex. "--format txt" -> PERUN_FORMAT=txt

- Local INI file

  Perun will look into the cwd for ".perun.ini" file, where options can be fixed for the directory.

  Example:

  ```ini
  [post-processing]
  pue = 1.58
  emissions_factor = 0.262
  price_factor = 34.6

  [monitor]
  sampling_rate = 1

  [output]
  app_name
  run_id
  format = text
  data_out = ./perun_results
  depth
  raw = False

  [benchmarking]
  bench_enable = False
  bench_rounds = 10
  bench_warmup_rounds = 1

  [debug]
  log_lvl = ERROR
  ```

  The location of the file can be changed using the option "-c" or "PERUN_CONFIGURATION".

- Global INI file

  If the file ~/.config/perun.ini is found, perun will override the default configuration with the contents of the file.

### Priority

CMD LINE and ENV > Local INI > Global INI > Default options


## Data Output Structure

When exporting data to machine readable formats like json, pickle, and hdf5, perun stores the data in a hierarchical format, with the application and individual runs at the root of data tree, and individual sensors and raw data a in the leafs. When processing, the data is propagated from the leafs (sensors), all the way to the root, where a aggregated statistics about the application are gatherd.

<div align="center">
  <img src="https://raw.githubusercontent.com/Helmholtz-AI-Energy/perun/main/docs/images/data_structure.png">
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/Helmholtz-AI-Energy/perun/main/docs/images/perun.svg">
</div>

Have you ever wondered how much energy is used when training your neural network on the MNIST dataset? Want to get scared because of impact you are having on the evironment while doing "valuable" research? Are you interested in knowing how much carbon you are burning playing with DALL-E just to get attention on twitter? If the thing that was missing from your machine learning workflow was existential dread, this is the correct package for you!

## Installation

From PyPI:

```console
pip install perun
```

From Github:

```console
pip install git+https://github.com/Helmholtz-AI-Energy/perun
```

### MPI Support

If your python program makes use of MPI, make sure mpi4py is installed.

```console
pip install mpi4py
```

## Usage

### Command line

To get a quick report of the power usage of a python script simply run

```console
perun --format yaml monitor path/to/your/script.py [args]
```

Or

```console
python -m perun --format json -o results/ monitor path/to/your/script.py [args]
```

#### Subcommands

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
  --format [text|json|hdf5|pickle|csv]
                                  Report format.
  --data_out DIRECTORY            Where to save the output files, defaults to
                                  the current working directory.
  --raw / --no-raw                Use the flag '--raw' if you need access to
                                  all the raw data collected by perun. The
                                  output will be saved on an hdf5 file on the
                                  perun data output location.
  --frequency FLOAT               sampling frequency (in Hz)
  --pue FLOAT                     Data center Power usage efficiency
  --emissions-factor FLOAT        Emissions factor at compute resource
                                  location
  --price-factor FLOAT            Electricity price factor at compute resource
                                  location
  -l, --log_lvl [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                  Loggging level
  --help                          Show this message and exit.

Commands:
  export    Export existing perun output file to another format.
  monitor   Gather power consumption from hardware devices while SCRIPT...
  sensors   Print sensors assigned to each rank by perun.
  showconf  Print current perun configuration in INI format.
```

#### monitor

Monitor energy usage of a python script.

```console
Usage: perun monitor [OPTIONS] SCRIPT [SCRIPT_ARGS]...

  Gather power consumption from hardware devices while SCRIPT [SCRIPT_ARGS] is
  running.

  SCRIPT is a path to the python script to monitor, run with arguments
  SCRIPT_ARGS.

Options:
  --help                        Show this message and exit.
```

#### sensors

Print available monitoring backends and each available sensors for each MPI rank.

```console
Usage: perun sensors [OPTIONS]

  Print sensors assigned to each rank by perun.

Options:
  --help  Show this message and exit.
```

#### export

Export an existing perun output file to another format.

```console
Usage: perun export [OPTIONS] INPUT_FILE OUTPUT_PATH
                    {text|json|hdf5|pickle|csv}

  Export existing perun output file to another format.

  Args:
    input_file (str): Exisiting perun output file.
    output_path (str): Location of the new file.
    output_format (str): Format of the new file.

Options:
  --help  Show this message and exit.
```

#### showconf

Prints the current option configurations based on the global, local configurations files and command line options.

```confg
Usage: perun showconf [OPTIONS]

  Print current perun configuration in INI format.

Options:
  --default  Print default configuration
  --help     Show this message and exit.
```

### Decorator

Or decorate the function that you want analysed

```python
from perun.decorator import monitor

@monitor(format="hdf5", data_out="results/")
def training_loop(args, model, device, train_loader, test_loader, optimizer, scheduler):
    for epoch in range(1, args.epochs + 1):
        train(args, model, device, train_loader, optimizer, epoch)
        test(model, device, test_loader)
        scheduler.step()
```

Optional arguments same as the command line.

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
  emissions-factor = 0.355
  price-factor = 41.59

  [monitor]
  frequency = 1

  [output]
  format = txt
  data_out = ./
  raw = False

  [debug]
  log_lvl = WARN
  ```

  The location of the file can be changed using the option "-c" or "PERUN_CONFIGURATION".

- Global INI file

  If the file ~/.config/perun.ini is found, perun will override the default configuration with the contents of the file.

### Priority

CMD LINE and ENV > Local INI > Global INI > Default options

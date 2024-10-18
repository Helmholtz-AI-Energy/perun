.. _usage:

Usage
=====

The `perun` command contains other subcommands that provide extra functionality. The command itself supports a couple of options, like setting a custom configuration or changing the logging level of the application. The information can be reviewd using the `--help` command flag.

.. code-block:: console

    Usage: perun [OPTIONS] COMMAND [ARGS]...

      Perun: Energy measuring and reporting tool.

    Options:
      --version                       Show the version and exit.
      -c, --configuration FILE        Path to configuration file
      -l, --log_lvl [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                      Loggging level
      --help                          Show this message and exit.



Monitor
-----------

To start monitoring your python applications, simply use

.. code-block:: console

    $ perun monitor your_app.py

This also applies MPI applications

.. code-block:: console

    $ mpirun -N 4 perun monitor your_app.py

perun will not disrupt your applications usage of MPI, and will collect hardware data from all the different nodes being used. At the end, you will get a single report based on the data from all the nodes and their hardware components.

To modify the peruns behaviour, the subcommand accepts options many configuration options that alter the monitoring or post processing process behaviour.

.. code-block:: console

    $ perun monitor --format json --sampling_period 5 your_app.py

The options can also be set as environmental variables.

.. code-block:: console

    $ PERUN_FORMAT=json perun monitor your_app.py


A combination of both also works. If you have a set of options that works for your workflow, you can save them on '.perun.ini' file, and perun will use them automatically. For more info on the configuration options and file, check the :ref:`configuration` section.

The monitor command will by default output two files. The first one is an HDF5 file, named after the monitored python script, which contains all the information gathered by perun over multiple runs. The data has a tree structure, where the root node contains a summary all the application runs. Subsequent nodes contain information about individual `perun monitor`


Perun is also capable of monitoring command line applications or executables without MPI. The command is the same, but the application name is the executable name.

.. code-block:: console

    $ perun monitor --binary your_executable [args]

Perun decorator
~~~~~~~~~~~~~~~

Perun cal also be run from within a script by using the perun decorator. This is particularly useful if the script needs to be run with another command line tool, or if the script is part of a larger application.

.. code-block:: python


    import perun

    @perun.perun(data_out="my_results", format="json")
    def main():
        your_code_goes.here()

    if __name__ == "__main__":
        main()

The decorator takes the same options as the monitor command, and can be set using the same environmental variables and configuration file. The decorator will also generate the same output files as the monitor command. Instead of using the perun commandline, the script can be run with the `python command`.

.. caution::
    The decorator will not work if the script is being run with the `perun monitor` command. The decorator will only work if the script is being run directly with the python interpreter.

.. caution::
    If the decorated function is run multiple times, perun will behave as if it was run multiple times, initializing everything multiple times. To avoid this overhead, ensure the decorated function is called a single time. If information about a particular function which runs multiple times is needed, check  out the :ref:`monitoring functions` section.

.. caution::
    If due to configuration options, perun is setup to run for multiple rounds, and the decorated function retuns a value, only the result of the last run will be returned.


Application Name and Run ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each time you use perun with a python script, perun assings it an application name and a run id. By default, the application name will be the name of the python script ('train.py' will have the name 'train'). The ID is an identifier of the particular execution of the application with perun, and it is by default the current date and time in ISO format. Both the application name and the run id will be used to name output files and internally by perun, and can be configured using command line arguments (`-n`, `--name` for the name, `-i`, `--run_id` for the id) or using the :ref:`configuration` file.

Multiple Rounds
~~~~~~~~~~~~~~~

perun has a special option `--rounds` which will run the application for multiple rounds using a single command, and generate statistics about the runtime, power consumption and device utilization. All the rounds will be associated with the same run id.

.. code-block:: console

    $ perun monitor your_app.py


Additionaly, there is a `--warmup-rounds` option if you want the application to execute without monitoring before the *real* rounds.


.. _monitoring functions:

Monitoring Functions
~~~~~~~~~~~~~~~~~~~~

Perun includes a function decorator that provides additional information about individual functions in the application. The decorator itself only stores timestamps at the start and the end of the function execution. Those timestamps are then used to extract the relevant information out of the sampled hardware data.

.. code-block:: python

    from perun import monitor

    @monitor()
    def main():
        your_code_goes.here()

Internally, perun will used the function name to identify it, and the internal id can be set using the option `region-name`.

.. _format:

Format
~~~~~~

In addition to HDF5 and text, perun support *json*, *pickle*, *csv* and a *bench* format. It can be setup from the start using the `--format` option in the monitor subcommand, or it can be generated later usint the :ref:`export` command.

**hdf5**

This is the default format, and the data structures on the file mirror the perun :py:class:`perun.data_model.data.DataNode` objects one-to-one. It includes the raw data metadata of each device, computational node, execution round, monitored function, run id and application.

**json**

Similar to hdf5, it keeps the internal perun data structure, but written as a json file.

**pickle**

Pickle is part of the python standart library and it stores python object in a binary format, meaning you can save the :py:class:`perun.data_model.data.DataNode` tree that is used by perun.

**csv**

This will create a csv table with all the raw data of an individual run. This will not include any device metadata.

**bench**

This format generates a json file that is meant to be used together with `Continuous Benchmark Github Action <https://github.com/marketplace/actions/continuous-benchmark>`_. It saves *customLessIsBetter* data points from the latest run, including monitored functions within the run, which can be used by the action to alert developers of performance degradations and create plots.

sensors
-------

To get a quick overview of which interfaces and information perun has access to, you can use the ``sensors`` subcommand.

.. code-block:: console

    $ perun sensors
    |           Sensor |   Source |          Device |   Unit |
    |-----------------:|---------:|----------------:|-------:|
    |       CPU_FREQ_0 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_1 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_2 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_3 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_4 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_5 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_6 |   psutil |  DeviceType.CPU |     Hz |
    |       CPU_FREQ_7 |   psutil |  DeviceType.CPU |     Hz |
    |        CPU_USAGE |   psutil |  DeviceType.CPU |      % |
    |  DISK_READ_BYTES |   psutil | DeviceType.DISK |      B |
    | DISK_WRITE_BYTES |   psutil | DeviceType.DISK |      B |
    |   NET_READ_BYTES |   psutil |  DeviceType.NET |      B |
    |  NET_WRITE_BYTES |   psutil |  DeviceType.NET |      B |
    |        RAM_USAGE |   psutil |  DeviceType.RAM |      B |

perun will print an overview of all the sensors that are available to perun, including the source of the data, the device type and the unit of the data. This can be useful to check if the sensors you need are available, or to get an overview of the data that perun can collect.

To print the sensors available in each MPI rank, use the option `--by_rank`. To see which sensors will be used during monitoring based on the current configuration file, use the option `--active`.


export
------

.. _export:


You can export existing perun output files to other formats using the export command.

.. code-block:: console

    $ perun export perun_results/forward_22149666.hdf5 csv

The command takes as a first argument one of the output files of perun, and as a second argument the format it will be exported to. The input file needs to be a ``json``, ``hdf5`` or ``pickle`` formated file, as the :py:class:`perun.data_model.data.DataNode` tree can only be reconstructed from those formats. The output format can be ``text``, ``json``, ``hdf5``, ``pickle``, ``csv`` and ``bench``.

showconf
--------

To get a quick overview of the current configuration that perun is using, use the ``showconf`` subcommand.

.. code-block:: console

   $ perun showconf
   [post-processing]
    power_overhead = 0
    pue = 1.0
    emissions_factor = 417.8
    price_factor = 0.3251
    price_unit = €

    [monitor]
    sampling_period = 1
    include_backends =
    include_sensors =
    exclude_backends =
    exclude_sensors =

    [output]
    app_name
    run_id
    format = text
    data_out = ./perun_results

    [benchmarking]
    rounds = 1
    warmup_rounds = 0
    metrics = runtime,energy
    region_metrics = runtime,power

    [benchmarking.units]
    joule = k
    second =
    percent =
    watt =
    byte = G

    [debug]
    log_lvl = WARNING


The command will print the current perun configuration in ``.ini`` format, which can be used as a starting point for your own ``.perun.ini`` file.

.. code-block:: console

    $ perun showconf > .perun.ini

To get the default configuration, simply add the ``--default`` flag.

.. code-block:: console

    $ perun showconf --default

metadata
--------

Similar to the `sensors` command, metadata will print a json object with some information about the system. It can be usefull to keep track of software dependencies, changes in the OS or the python version.

.. code-block:: json

    {
        "juan-20w000p2ge": {
            "libc_ver": "glibc 2.38",
            "_node": "juan-20w000p2ge",
            "architecture": "64bit ELF",
            "system": "Linux",
            "node": "juan-20w000p2ge",
            "release": "6.1.44-1-MANJARO",
            "version": "#1 SMP PREEMPT_DYNAMIC Wed Aug  9 09:02:26 UTC 2023",
            "machine": "x86_64",
            "_sys_version": "CPython 3.8.16   default Mar  3 2023 09:25:30 GCC 12.2.1 20230201",
            "python_implementation": "CPython",
            "python_version": "3.8.16",
            "python_version_tuple": "3 8 16",
            "python_build": "default Mar  3 2023 09:25:30",
            "python_compiler": "GCC 12.2.1 20230201",
            "platform": "Linux-6.1.44-1-MANJARO-x86_64-with-glibc2.34",
            "backends": {
                "Intel RAPL": {},
                "PSUTIL": {
                    "DISK_READ_BYTES": {
                        "source": "psutil 5.9.5"
                    },
                    "RAM_USAGE": {
                        "total": "16481222656",
                        "available": "7718731776",
                        "source": "psutil 5.9.5"
                    },
                    "CPU_USAGE": {
                        "source": "psutil 5.9.5"
                    },
                    "NET_WRITE_BYTES": {
                        "source": "psutil 5.9.5"
                    },
                    "DISK_WRITE_BYTES": {
                        "source": "psutil 5.9.5"
                    },
                    "NET_READ_BYTES": {
                        "source": "psutil 5.9.5"
                    }
                }
            }
        }
    }

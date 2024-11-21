.. _quick-start:

Quick Start
===========

.. hint::

   Check a `full example  <https://github.com/Helmholtz-AI-Energy/perun/blob/main/examples/torch_mnist/README.md>`_ on our github repository

To start using perun, the first step is to install it using pip.

.. code-block:: console

    $ pip install perun

After the installation is done, you can start monitoring your scripts using the following command.

.. code-block:: console

    $ perun monitor you_script.py

Once your code finishes running, you will find a new directory called ``perun_results`` with a text file named after the python script and the date. The text file will have a summarized report from perun.

.. code-block::

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


.. note::

    Depending on the hardware you are running and the available interfaces, the output might look different than the one listed here. For more details on the support data sources used by perun, check the :ref:`dependencies` section


The text report summarizes the data gathered while the application was running. Perun also makes all the raw data gathered from the hardware on an HDF5 file that is located on the same results folder. To explore the data manually, we recommend the Visual Studio Code extension `H5Web <https://marketplace.visualstudio.com/items?itemName=h5web.vscode-h5web>`_, to process it with python using `h5py <https://www.h5py.org/>`_, or to export using the :code:`perun export` subcommand (see :ref:`usage`).

The hdf5 file collects information over multiple runs of the application, adding a new section every time the application is executed using perun. The simplifies studying the behaviour of the application over time, make the last line in the summary report posible.

Function Monitoring
-------------------

To get information the power consumption, runtime and hardware utilization of individual functions while the application is being monitored, perun includes a function decorator.

.. code-block:: python

    import time
    from perun import monitor

    @monitor()
    def main(n: int):
        time.sleep(n)


This will add a new section to the text report and to the hdf5 file with the individual function profiles.

.. code-block::

    Monitored Functions

    |   Round # | Function                    |   Avg Calls / Rank | Avg Runtime     | Avg Power        | Avg CPU Util   | Avg GPU Mem Util   |
    |----------:|:----------------------------|-------------------:|:----------------|:-----------------|:---------------|:-------------------|
    |         0 | main                        |                  1 | 993.323±0.587 s | 964.732±0.499 W  | 3.244±0.003 %  | 35.091±0.526 %     |
    |         0 | prepare_train_features      |                 88 | 0.383±0.048 s   | 262.305±19.251 W | 4.541±0.320 %  | 3.937±0.013 %      |
    |         0 | prepare_validation_features |                 11 | 0.372±0.079 s   | 272.161±19.404 W | 4.524±0.225 %  | 4.490±0.907 %      |


MPI Compatibility
-----------------

Perun is capable of handling applications that make use of MPI using the `mpi4py <https://mpi4py.readthedocs.io/en/stable/>`_ library without any need to reconfigure or modify the existing code.

.. code-block:: console

    mpirun -n 4 perun monitor mpi_app.py

Perun has multiple subcommands and configuration options to accomodate various use cases and workflows. For more information, check out the :ref:`usage` and :ref:`configuration` sections of the documentation, or use the help flag :code:`-h` in the command line.

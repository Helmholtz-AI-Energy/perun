Quick Start
===========

To start using perun, the first step is to install it using pip.

.. code-block:: console

    $ pip install perun

After the installation is done, you can start monitoring your scripts using the following command.

.. code-block:: console

    $ perun monitor you_script.py

Once your code finishes running, you will find a new directory called ``perun_results`` with a text file named after the python script and the date. The text file will have a summarized report from perun.

.. code-block::

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

.. note::

    Depending on the hardware you are running and the available interfaces, the output might look different than the one listed here. For more details on the support data sources used by perun, check the :ref:`dependencies` section


perun can also be used as a function decorator to target specific code regions.

.. code-block:: python

    import time
    from perun.decorator import monitor

    @monitor()
    def your_sleep_function(n: int):
        time.sleep(n)


If you need more detailed output or access to the raw data that perun gathered, you can configure python both in the command line or as decorator to get the data you want.


.. code-block:: console

    $ perun --format json --raw monitor you_script.py

The same options can be given to the function decorator.

.. code-block:: python

    import time
    from perun.decorator import monitor

    @monitor(format="hdf5", sampling_rate=2)
    def your_sleep_function(n: int):
        time.sleep(n)

perun has more subcommand and configuration, to accomodate various use cases and workflows. For more information, check out the :ref:`usage` and :ref:`configuration` sections of the documentation.

.. image:: https://raw.githubusercontent.com/Helmholtz-AI-Energy/perun/main/docs/images/full_logo.svg

| |fair-software| |openssf| |zenodo| |license| |docs|
| |pypi-version| |python-version| |pypi-downloads| |black| |codecov|

.. |fair-software| image:: https://img.shields.io/badge/fair--software.eu-%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F%20%20%E2%97%8F-green
   :target: https://fair-software.eu
.. |openssf| image:: https://bestpractices.coreinfrastructure.org/projects/7253/badge
   :target: https://bestpractices.coreinfrastructure.org/projects/7253
.. |zenodo| image:: https://zenodo.org/badge/523363424.svg
   :target: https://zenodo.org/badge/latestdoi/523363424
.. |pypi-version| image:: https://img.shields.io/pypi/v/perun
.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/perun
.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
.. |codecov| image:: https://codecov.io/gh/Helmholtz-AI-Energy/perun/graph/badge.svg?token=9O6FSJ6I3G
   :target: https://codecov.io/gh/Helmholtz-AI-Energy/perun
.. |python-version| image:: https://img.shields.io/badge/Python-3.9+-blue.svg
   :target: https://www.python.org/downloads/
.. |license| image:: https://img.shields.io/badge/License-BSD_3--Clause-blue.svg
   :target: https://opensource.org/licenses/BSD-3-Clause
.. |docs| image:: https://readthedocs.org/projects/perun/badge/?version=latest
   :target: https://perun.readthedocs.io/en/latest/?badge=latest

===============================================================

*perun* is a Python package that calculates the energy consumption of Python scripts by sampling usage statistics from your Intel, Nvidia or AMD hardware components. It can handle MPI applications, gather data from hundreds of nodes, and accumulate it efficiently. *perun* can be used as a command-line tool or as a function decorator in Python scripts.

Check out the `docs <https://perun.readthedocs.io/en/latest/>`_ or a working `example <https://github.com/Helmholtz-AI-Energy/perun/blob/main/examples/torch_mnist/README.md>`_!

Key Features
------------

- Measures energy consumption of Python scripts and binaries, supporting different hardware configurations
- Capable of handling MPI applications, gathering data from hundreds of nodes efficiently
- Monitor individual functions using decorators
- Tracks energy usage of the application over multiple executions
- Easy to benchmark applications and functions
- Experimental!: Can monitor any non-distributed command line application

-----------------------------------------------------------------


Quick Start
-----------

Installation
^^^^^^^^^^^^

From PyPI:

.. code:: console

    $ pip install perun

Extra dependencies like *nvidia-smi*, *rocm-smi* and *mpi4py* can be installed using pip as well:

.. code:: console

    $ pip install perun[nvidia, rocm, mpi]

From Github:

.. code:: console

    $ pip install git+https://github.com/Helmholtz-AI-Energy/perun

Command Line
^^^^^^^^^^^^

To use *perun* as a command-line tool:

.. code:: console

    $ perun monitor path/to/your/script.py [args]

*perun* will output two files, an HDF5 style containing all the raw data that was gathered, and a text file with a summary of the results.

.. code:: text

    PERUN REPORT

    App name: finetune_qa_accelerate
    First run: 2023-08-15T18:56:11.202060
    Last run: 2023-08-17T13:29:29.969779

    RUN ID: 2023-08-17T13:29:29.969779

    +-----------+------------------------+-----------+-------------+--------------+-------------+-------------+-------------+---------------+-------------+
    | Round #   | Host                   | RUNTIME   | ENERGY      | CPU_POWER    | CPU_UTIL    | GPU_POWER   | GPU_MEM     | DRAM_POWER    | MEM_UTIL    |
    +===========+========================+===========+=============+==============+=============+=============+=============+===============+=============+
    | 0         | hkn0432.localdomain    | 995.967 s | 960.506 kJ  | 231.819 W    | 3.240 %     | 702.327 W   | 55.258 GB   | 29.315 W      | 0.062 %     |
    | 0         | hkn0436.localdomain    | 994.847 s | 960.469 kJ  | 235.162 W    | 3.239 %     | 701.588 W   | 56.934 GB   | 27.830 W      | 0.061 %     |
    | 0         | All                    | 995.967 s | 1.921 MJ    | 466.981 W    | 3.240 %     | 1.404 kW    | 112.192 GB  | 57.145 W      | 0.061 %     |

    The application has been run 7 times. In total, it has used 3.128 kWh, released a total of 1.307 kgCO2e into the atmosphere, and you paid 1.02 € in electricity for it.


Binary support (experimental)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*perun* is capable of monitoring simple applications written in other languages:

.. code:: console

    $ perun monitor --binary path/to/your/executable [args]

Function Monitoring
^^^^^^^^^^^^^^^^^^^

Using a function decorator

.. code:: python

    import time
    from perun import monitor

    @monitor()
    def main(n: int):
        time.sleep(n)

After running with ``perun monitor``, the report will contain:

.. code:: text

    Monitored Functions

    +-----------+----------------------------+---------------------+------------------+--------------------+------------------+-----------------------+
    | Round #   | Function                   | Avg Calls / Rank    | Avg Runtime      | Avg Power          | Avg CPU Util     | Avg GPU Mem Util      |
    +===========+============================+=====================+==================+====================+==================+=======================+
    | 0         | main                       | 1                   | 993.323±0.587 s  | 964.732±0.499 W    | 3.244±0.003 %    | 35.091±0.526 %        |
    | 0         | prepare_train_features     | 88                  | 0.383±0.048 s    | 262.305±19.251 W   | 4.541±0.320 %    | 3.937±0.013 %         |
    | 0         | prepare_validation_features| 11                  | 0.372±0.079 s    | 272.161±19.404 W   | 4.524±0.225 %    | 4.490±0.907 %         |


MPI
^^^

*perun* is compatible with MPI applications using ``mpi4py``:

.. code:: console

    $ mpirun -n 8 perun monitor path/to/your/script.py

Docs
----

See the `documentation <https://perun.readthedocs.io/en/latest/>`_ or `examples <https://github.com/Helmholtz-AI-Energy/perun/tree/main/examples>`_ for more details.

Citing perun
------------

If you found *perun* useful, please cite the conference paper:

::

    Gutiérrez Hermosillo Muriedas, J.P., Flügel, K., Debus, C., Obermaier, H., Streit, A., Götz, M.:
    perun: Benchmarking Energy Consumption of High-Performance Computing Applications.
    In: Cano, J., Dikaiakos, M.D., Papadopoulos, G.A., Pericàs, M., and Sakellariou, R. (eds.)
    Euro-Par 2023: Parallel Processing. pp. 17–31. Springer Nature Switzerland, Cham (2023).
    https://doi.org/10.1007/978-3-031-39698-4_2

.. code-block:: bibtex

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
     title="perun: Benchmarking Energy Consumption of High-Performance Computing Applications",
     booktitle="Euro-Par 2023: Parallel Processing",
     year="2023",
     publisher="Springer Nature Switzerland",
     address="Cham",
     pages="17--31",
     isbn="978-3-031-39698-4"
   }

===========================================

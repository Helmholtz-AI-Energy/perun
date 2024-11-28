.. _installation:

Installation
============

The latest release of **perun** can be installed using pip

.. code-block:: console

    $ pip install perun

or if you need the latests updates, you can install from the main branch of github at you own risk

.. code-block:: console

    $ pip install https://github.com/Helmholtz-AI-Energy/perun

If you are going to work with MPI or GPUs, you can install it as extra dependencies.

.. code-block:: console

    $ pip install perun[mpi, nvidia, rocm]

If you want to get the source code and modify it, you can clone the source code using git.

.. code-block:: console

    $ git clone https://github.com/Helmholtz-AI-Energy/perun

perun uses `poetry <https://python-poetry.org/>`_ as a packaging and dependencies manager. Follow the instructions on the documentation on how to install **poetry** on you platform. Once poetry is installed, use the command

.. code-block:: console

    $ poetry install

to install the mandatory dependencies. To install the complete development environment, the extra ``--with dev`` needs to be appended to the command.

After the installation is done, you can open a shell with the environment using the command

.. code-block:: console

    $ poetry shell

or you can run individual commands using the ``run`` poetry subcommand. Check the `poetry documentation <https://python-poetry.org/>`_ for more information.


.. _dependencies:

Dependencies
------------

In order to get energy readings out of your hardware components, it is important that perun has access to the relevant interfaces.

CPU
~~~

Supported backends:

 - CPU energy: Powercap RAPL using `powercap <https://github.com/powercap/powercap>`_ for linux machines, supports recent Intel and AMD CPUs.
 - CPU utilization: `psutil <https://github.com/giampaolo/psutil>`_

Currently, cpu energy readings from perun only support linux environments with read access to the *powercap-rapl* interface, which can only be read by ``root`` on Linux 5.10 and later. If that is the case, please contact you system admin for solutions. We are currently working on alternative methods to provide energy readings.

GPU
~~~

Supported backends:

 - NVIDIA GPU power draw: `NVIDIA NVML <https://developer.nvidia.com/nvidia-management-library-nvml>`_ using nvidia-ml-py.
 - AMD GPU power draw: `ROCM SMI <https://github.com/RadeonOpenCompute/pyrsmi>`_ using pyrsmi.

DRAM
~~~~

Supported backends:
 - DRAM energy: Intel RAPL using `powercap <https://github.com/powercap/powercap>`_ for linux machines.

Misc
~~~~

Supported backends:
 - Storage IO: `psutil <https://github.com/giampaolo/psutil>`_
 - Network IO: `psutil <https://github.com/giampaolo/psutil>`_

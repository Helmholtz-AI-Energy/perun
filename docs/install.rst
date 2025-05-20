.. _installation:

Installation
============

The latest release of **perun** can be installed using pip

.. code:: console

    $ pip install perun

or if you need the latests updates, you can install from the main branch of github at you own risk

.. code:: console

    $ pip install git+https://github.com/Helmholtz-AI-Energy/perun

If you are going to work with MPI or GPUs, you can install it as extra dependencies.

.. code:: console

    $ pip install perun[mpi, nvidia, rocm]


Development environment
-----------------------

If you want to get the source code and modify it, you can clone the source code using git.

.. code:: console

    $ git clone https://github.com/Helmholtz-AI-Energy/perun

Afterwards, you can install an editable version of perun with the development dependecies:

.. code:: console

    $ pip install -e .[dev]


.. _dependencies:

Dependencies
------------

In order to get energy readings out of your hardware components, it is important that perun has access to the relevant interfaces.

CPU
~~~

Supported backends:

* **CPU energy**: Powercap RAPL using `powercap <https://github.com/powercap/powercap>`_ for linux machines, supports recent Intel and AMD CPUs.
* **CPU utilization**: `psutil <https://github.com/giampaolo/psutil>`_

.. important::

    Currently, cpu energy readings from perun only support linux environments with read access to the `powercap-rapl interface <https://www.kernel.org/doc/html/latest/power/powercap/powercap.html>`_, which can only be read by **root** on Linux 5.10 and later. If that is the case, please contact you system admin for solutions. We are currently working on alternative methods to provide energy readings.

GPU
~~~

Supported backends:

* **NVIDIA GPU power draw**: `NVIDIA NVML <https://developer.nvidia.com/nvidia-management-library-nvml>`_ using nvidia-ml-py.
* **AMD GPU power draw**: `AMD SMI <https://github.com/ROCm/amdsmi>`_ using `amdsmi`.

DRAM
~~~~

Supported backends:

* **DRAM energy**: Intel RAPL using `powercap <https://github.com/powercap/powercap>`_ for linux machines.
* **DRAM memory utilization**: `psutil <https://github.com/giampaolo/psutil>`_

Misc
~~~~

Supported backends:

* **Storage IO**: `psutil <https://github.com/giampaolo/psutil>`_
* **Network IO**: `psutil <https://github.com/giampaolo/psutil>`_

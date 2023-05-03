.. perun documentation master file, created by
   sphinx-quickstart on Mon Apr 24 09:25:39 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. image:: images/full_logo.svg

|

**perun** is a Python package that calculates the energy consumption of Python scripts by sampling usage statistics from Intel RAPL, Nvidia-NVML, and psutil. It can handle MPI applications, gather data from hundreds of nodes, and accumulate it efficiently. perun can be used as a command-line tool or as a function decorator in Python scripts.

.. note::
   This project is under active development. For any issues, features requests, or if you would like to contribute, our `github page`_ page is the place to go.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   quickstart
   install
   usage
   configuration
   data


.. Links
.. _github page: https://github.com/Helmholtz-AI-Energy/perun

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

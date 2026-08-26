.. _hdf5:

Working with the HDF5 output
============================

By default ``perun`` writes an HDF5 file next to your script (named after the
application). It contains **everything** perun collected: the full data tree,
per-device raw samples, computed metrics, metadata, and monitored regions. This
page shows how to open that file and get the data out, either with plain
``h5py``/``pandas`` or with perun's own command line utilities — no need to
learn perun's internal Python API first.

.. contents::
   :local:
   :depth: 2


File layout
-----------

The file mirrors perun's :py:class:`perun.data_model.data.DataNode` tree
one-to-one. Every node is an HDF5 **group**; the tree goes from the application
at the root down to individual sensors at the leaves:

.. code-block:: text

    <app_name>/                      # APP        (group)
    ├── attrs: type, creation_dt, last_execution_dt, perun_version, ...
    ├── metrics/                     # aggregated Stats for the whole app
    │   └── <METRIC_NAME>/           # e.g. ENERGY, RUNTIME, CO2, MONEY
    │       └── attrs: type, unit, mag, dtype, sum, mean, std, min, max
    └── nodes/
        └── <run_id>/                # MULTI_RUN  (a group of --rounds runs)
            ├── metrics/             # Stats across the rounds
            └── nodes/
                └── <round_n>/       # RUN        (one execution)
                    ├── metrics/
                    ├── regions/     # optional, monitored functions
                    └── nodes/
                        └── <hostname>/          # NODE (one compute node)
                            ├── metrics/
                            └── nodes/
                                └── <device_group>/   # DEVICE_GROUP
                                    └── nodes/
                                        └── <sensor_id>/   # SENSOR (leaf)
                                            ├── metrics/
                                            └── raw_data/   # the samples

Key conventions:

- **Node type** is stored in each group's ``type`` attribute (``APP``,
  ``MULTI_RUN``, ``RUN``, ``NODE``, ``DEVICE_GROUP``, ``SENSOR``).
- **Metadata** is stored as group attributes (all serialized to strings).
- **Metrics** live under a ``metrics/`` subgroup. A leaf ``Metric`` has a
  ``value`` attribute; an aggregated ``Stats`` has ``sum``/``mean``/``std``/
  ``min``/``max`` attributes. Both carry unit info in ``unit``, ``mag`` (the
  magnitude/SI prefix) and ``dtype``.
- **Raw samples** live under ``raw_data/`` on sensor nodes, as two datasets:
  ``timesteps`` and ``values`` (plus an optional ``alt_values`` — for energy
  sensors, ``values`` becomes derived power and ``alt_values`` keeps the
  original energy counter).


Quick look with the HDF5 tooling
--------------------------------

If you just want to browse the structure, the ``h5py`` and ``hdf5`` packages
ship the ``h5ls`` / ``h5dump`` command line tools:

.. code-block:: console

    $ h5ls -r my_app.hdf5 | head
    /                        Group
    /my_app                  Group
    /my_app/metrics          Group
    /my_app/metrics/ENERGY   Group
    /my_app/nodes            Group
    ...


Reading metrics with ``h5py``
-----------------------------

.. code-block:: python

    import h5py

    with h5py.File("my_app.hdf5", "r") as f:
        app = f[list(f.keys())[0]]          # the single root (application) group

        # Application-level aggregated metrics (Stats):
        energy = app["metrics"]["ENERGY"]
        print("unit:", energy.attrs["unit"], "mag:", energy.attrs["mag"])
        print("total energy:", energy.attrs["sum"])
        print("mean per run:", energy.attrs["mean"])

        # Iterate every run and read its runtime/energy:
        for run_id, mr in app["nodes"].items():
            for round_n, run in mr["nodes"].items():
                m = run["metrics"]
                print(run_id, round_n,
                      "runtime", m["RUNTIME"].attrs["value"],
                      "energy", m["ENERGY"].attrs["value"])

.. note::

    Values are stored in the magnitude given by the ``mag`` attribute (an SI
    prefix factor, e.g. ``1000`` for kilo). Multiply the stored value by ``mag``
    to get the base-unit value.


Reading raw samples with ``h5py`` + ``pandas``
----------------------------------------------

Every sensor keeps its time series under ``raw_data/``:

.. code-block:: python

    import h5py
    import pandas as pd

    def sensor_timeseries(path):
        rows = []
        with h5py.File(path, "r") as f:
            app = f[list(f.keys())[0]]
            for run_id, mr in app["nodes"].items():
                for round_n, run in mr["nodes"].items():
                    for host, host_node in run["nodes"].items():
                        for grp, dg in host_node["nodes"].items():
                            for sensor_id, sensor in dg["nodes"].items():
                                if "raw_data" not in sensor:
                                    continue
                                raw = sensor["raw_data"]
                                ts = raw["timesteps"][:]
                                vals = raw["values"][:]
                                for t, v in zip(ts, vals):
                                    rows.append((run_id, round_n, host,
                                                 sensor_id, t, v))
        return pd.DataFrame(
            rows,
            columns=["run_id", "round", "host", "sensor", "timestep", "value"],
        )

    df = sensor_timeseries("my_app.hdf5")
    print(df.head())


Exporting from the command line
-------------------------------

If you would rather not touch ``h5py`` at all, use ``perun export`` to convert
an existing output file into an easier-to-consume format. The input can be any
of perun's structured formats (``hdf5``, ``json``, ``pickle``) and the output
one of ``csv``, ``json``, ``bench``, ``text`` (and back to ``hdf5``/``pickle``):

.. code-block:: console

    # Raw per-sample table for the last run, as CSV:
    $ perun export my_app.hdf5 csv

    # Pick a specific run id:
    $ perun export -i 2024-05-20T12:00:00 my_app.hdf5 csv

    # Human-readable summary table:
    $ perun export my_app.hdf5 text

The ``csv`` export produces one row per sample with the columns
``run id, hostname, device_group, sensor, unit, magnitude, timestep, value`` —
ready to load with :func:`pandas.read_csv` and plot.

.. code-block:: python

    import pandas as pd

    df = pd.read_csv("my_app_<run_id>.csv")
    # Average power draw per sensor over time, for example:
    df.groupby("sensor")["value"].mean()


Loading back into perun
-----------------------

If you want the rich Python objects (metrics with units, regions, etc.) rather
than flat tables, you can re-import the tree:

.. code-block:: python

    from pathlib import Path
    from perun.io.io import importFrom, IOFormat

    data = importFrom(Path("my_app.hdf5"), IOFormat.HDF5)
    print(data.id, data.metrics.keys())

See :ref:`data` for a description of the ``DataNode`` structure returned here.

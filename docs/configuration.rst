.. _configuration:

Configuration
=============

perun can be configured to fit different types of goals and workflows, either on the command line, decorator or using a configuration file. For more details on how use the options, go to the :ref:`usage` section.

The following table list the current options available, their default values, and a brief description.

Options
-------

.. csv-table:: Configuration Options
    :header: "Category", "Name", "Default", "Description"

    "post-processing", "power_overhead", 0.0, "Estimated power consumption of non-measured hardware components in Watts. Will be added to the power draw and energy consumed of individual nodes. Defaults to 0 Watts"
    "post-processing", "pue", 1.0, "Power Usage Effectiveness: A measure of a data centers efficiency, calculated as
    PUE = Total facilitty energy / IT equipment energy. Calculated for each run."
    "post-processing", "emissions_factor", 417.80, "Average carbon intensity of electricity (gCO2e/kWh). Calculated for each run. Source: https://ourworldindata.org/grapher/carbon-intensity-electricity"
    "post-processing", "price_factor", 0.3251, "Power to Currency conversion factor (Currency/kWh). Calculated for each run. Source : https://www.stromauskunft.de/strompreise/"
    "post-processing", "price_unit", €, "Currency Icon"
    "monitor", "sampling_period", 1, "Seconds between measurements"
    "monitor", "include_backends", "", "Space separated list of backends to include during monitoring. If empty, all backends will be included. Cannot be used together with `exclude_backends`."
    "monitor", "exclude_backends", "", "Space separated list of backends to exclude during monitoring. If empty, all backends will be included. Cannot be used together with `include_backends`."
    "monitor", "include_sensors", "", "Space separated list of sensors to include during monitoring. If empty, all sensors will be included. Cannot be used together with `exclude_sensors`."
    "monitor", "exclude_sensors", "", "Space separated list of sensors to exclude during monitoring. If empty, all sensors will be included. Cannot be used together with `include_sensors`."
    "output", "app_name", None, "Name to identify the app. If **None**, name will be based on the file or function name."
    "output", "run_id", None, "ID of the current run. If **None**, the current date and time will be used. If **SLURM**, perun will look for the environmental variable **SLURM_JOB_ID** and use that."
    "output", "format", "text", "Output report format [text, pickle, csv, hdf5, json, bench]"
    "output", "data_out", "./perun_results", "perun output location."
    "benchmarking", "rounds", 1, "Number of times the application is run."
    "benchmarking", "warmup_rounds", 0, "Number of warmup rounds to run before starting the benchmarks."
    "benchmarking", "metrics", "runtime,energy", "List of metrics to present on the benchmarking report."
    "benchmarking", "region_metrics", "runtime,power", "List of metrics to present on the region report."
    "benchmarking.units", "joule", "k", "Default order of magnitude to present total energy for the benchmarking report."
    "benchmarking.units", "second", "", "Default order of magnitude to present runtime information for the benchmarking report."
    "benchmarking.units", "percent", "", "Default order of magnitude to present percentages for the benchmarking report."
    "benchmarking.units", "watt", "k", "Default order of magnitude to present power draw for the benchmarking report."
    "benchmarking.units", "byte", "G", "Default order of magnitude to present number of bytes for the benchmarking report."
    "debug", "log_lvl", "WARNING", "Change logging output [DEBUG, INFO, WARNING, ERROR, CRITICAL]"

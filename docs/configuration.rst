.. _configuration:

Configuration
=============

perun can be configured to fit different types of goals and workflows, either on the command line, decorator or using a configuration file. For more details on how use the options, go to the :ref:`usage` section.

The following table list the current options available, their default values, and a brief description.

Options
-------

.. csv-table:: Configuration Options
    :header: "Name", "Default", "Description"

    "power_overhead", 0.0, "Estimated power consumption of non-measured hardware components in Watts. Will be added to the power draw and energy consumed of individual nodes. Defaults to 0 Watts"
    "pue", 1.0, "Power Usage Effectiveness: A measure of a data centers efficiency, calculated as
    PUE = Total facilitty energy / IT equipment energy. Calculated for each run."
    "emissions_factor", 417.80, "Average carbon intensity of electricity (gCO2e/kWh). Calculated for each run. Source: https://ourworldindata.org/grapher/carbon-intensity-electricity"
    "price_factor", 0.3251, "Power to Currency conversion factor (Currency/kWh). Calculated for each run. Source : https://www.stromauskunft.de/strompreise/"
    "price_unit", €, "Currency Icon"
    "sampling_rate", 1, "Seconds between measurements"
    "app_name", None, "Name to identify the app. If **None**, name will be based on the file or function name."
    "run_id", None, "ID of the current run. If **None**, the current date and time will be used. If **SLURM**, perun will look for the environmental variable **SLURM_JOB_ID** and use that."
    "format", "text", "Output report format [text, pickle, csv, hdf5, json, bench]"
    "data_out", "./perun_results", "perun output location"
    "rounds", 5, "Number of times the application is run"
    "warmup_rounds", 1, "Number of warmup rounds to run before starting the benchmarks."
    "log_lvl", "WARNING", "Change logging output [DEBUG, INFO, WARNING, ERROR, CRITICAL]"

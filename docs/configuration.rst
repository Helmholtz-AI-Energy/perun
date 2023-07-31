.. _configuration:

Configuration
=============

perun can be configured to fit different types of goals and workflows, either on the command line, decorator or using a configuration file. For more details on how use the options, go to the :ref:`usage` section.

The following table list the current options available, their default values, and a brief description.

Options
-------

.. csv-table:: Configuration Options
    :header: "Name", "Default", "Description"

    "pue", 1.58, "Power Usage Effectiveness: A measure of a data centers efficiency, calculated as
    PUE = Total facilitty energy / IT equipment energy"
    "emissions_factor", 417.80, "Average carbon intensity of electricity (gCO2e/kWh). Source: https://ourworldindata.org/grapher/carbon-intensity-electricity"
    "price_factor", 32.51, "Power to Euros conversion factor (Cent/kWh). Source : https://www.stromauskunft.de/strompreise/"
    "sampling_rate", 1, "Seconds between measurements"
    "app_name", None, "Name to identify the app. If **None**, name will be based on the file or function name. If **SLURM**, perun will look for the environmental variable **SLURM_JOB_NAME** and use that."
    "run_id", None, "ID of the current run. If **None**, the current date and time will be used. If **SLURM**, perun will look for the environmental variable **SLURM_JOB_ID** and use that."
    "format", "text", "Output report format [text, pickle, csv, hdf5, json, bench]"
    "data_out", "./perun_results", "perun output location"
    "raw", False, "If output file should include raw data"
    "rounds", 5, "Number of times a the application is run"
    "warmup_rounds", 1, "Number of warmup rounds to run before starting the benchmarks."
    "log_lvl", "ERROR", "Change logging output [DEBUG, INFO, WARNING, ERROR, CRITICAL]"

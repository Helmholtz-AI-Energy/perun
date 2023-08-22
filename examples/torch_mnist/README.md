# Torch MNIST Example

This directory contains everything to you need to start using **perun** in your workflows. As an example, we are using the [torch](https://pytorch.org/) package to train a neural network to recognize the handwritten digits using the MNIST dataset.

## Setup

It is recommended that you create a new environment with any new project using the *venv* package

```console
python -m venv venv/perun-example
source venv/perun-example/bin/activate
```

or with *conda*

```console
conda create --name perun-example
conda activate perun-example
```

Once your new enviornment is ready, you can install the dependencies for the example.

```console
pip install -r requirements.txt
```

This includes **perun** and the scripts dependencies. The the root of the project includes a minimal configuration file example.perun.ini*, with some basic options. More details on the configuration options can be found [in the docs](https://perun.readthedocs.io/en/latest/configuration.html).

To make sure **perun** was installed properly and that it has access to some hardware sensors, run the command

```console
perun sensors
```

## Monitoring

Now everything is ready to start getting data. To get monitor your script a single time, simply run:

```console
perun monitor torch_mnist.py
```

After the script finishes running, a folder *perun_results* will be created containing the consumption report of your application as a text file, including the all the raw data saved in an hdf5 file.

To explored the contents of the hdf5 file, we recomed the **h5py** library or the [myHDF5](https://myhdf5.hdfgroup.org) website.

The text report from running the MNIST example should look like this:

```text
PERUN REPORT

App name: torch_mnist
First run: 2023-08-22T17:10:52.864155
Last run: 2023-08-22T17:10:52.864155


RUN ID: 2023-08-22T17:10:52.864155

|   Round # | Host            | RUNTIME   | CPU_UTIL   | MEM_UTIL   |
|----------:|:----------------|:----------|:-----------|:-----------|
|         0 | juan-20w000p2ge | 330.841 s | 63.367 %   | 0.559 %    |
|         0 | All             | 330.841 s | 63.367 %   | 0.559 %    |

Monitored Functions

|   Round # | Function    |   Avg Calls / Rank | Avg Runtime     | Avg Power     | Avg CPU Util   | Avg GPU Mem Util   |
|----------:|:------------|-------------------:|:----------------|:--------------|:---------------|:-------------------|
|         0 | train       |                  1 | 329.300±0.000 s | 0.000±0.000 W | 63.594±0.000 % | 0.000±0.000 %      |
|         0 | train_epoch |                  5 | 61.563±2.827 s  | 0.000±0.000 W | 64.669±2.130 % | 0.000±0.000 %      |
|         0 | test        |                  5 | 4.297±0.069 s   | 0.000±0.000 W | 46.278±1.119 % | 0.000±0.000 %      |

The application has run been run 1 times.
```

## Benchmarking

Benchmarking mode can help users obtain more indept data about the runtime and energy consumption of your scripts, by running the application multiple times and providing statistics like mean, std, min and max values for the usual measurements. To use benchmarking mode, add the `--bench` option to the perun command:


```console
perun monitor --rounds 5 torch_mnist.py
```

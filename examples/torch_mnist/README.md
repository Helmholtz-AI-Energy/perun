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

This includes **perun** and the scripts dependencies. The example includes a minimal configuration file *.perun.ini*, with some basic options. More details on the configuration options can be found [in the docs](https://perun.readthedocs.io/en/latest/configuration.html).

To make sure **perun** was installed properly and that it has access to some hardware sensors, run the command

```console
perun sensors
```

## Monitoring

Now everything is ready to start getting data. To get monitor your script a single time, simply run:

```console
perun monitor torch_mnist.py
```

After the script finishes running, a folder *perun_results* will be created containing the consumption report of your application as a text file.

## Benchmarking

Benchmarking mode can help users obtain more indept data about the runtime and energy consumption of your scripts, by running the application multiple times and providing statistics like mean, std, min and max values for the usual measurements. To use benchmarking mode, add the `--bench` option to the perun command:


```console
perun --bench monitor torch_mnist.py
```

 > The application will be run 10 times, when benchmarking is active. If you want to reduce the runtime of the example, either reduce the number of training epochs ```... torch_mnist.py --epochs 1``` or reduce the number of rounds **perun** runs the applications ```perun --bench --bench_rounds 5 monitor ...```.

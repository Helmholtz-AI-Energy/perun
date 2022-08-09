# perun

Have you ever wondered how much energy is used when training your neural network on the MNIST dataset? Want to get scared because of impact you are having on the evironment while doing "valuable" research? Are you interested in knowing how much carbon you are burning playing with DALL-E just to get attention on twitter? If the thing that was missing from your machine learning workflow was existential dread, this is the correct package for you!

## Installation

```$ pip install git+https://github.com/Helmholtz-AI-Energy/perun```

### Parallel h5py

To build h5py with mpi support:

```CC=mpicc HDF5_MPI="ON" pip install --no-binary h5py h5py```

## Usage

### Command line

To get a quick report of the power usage of a python script simply run

```$ perun monitor path/to/your/script.py [args]```

### Decorator

Or decorate the function that you want analysed

```python
from perun.monitor import monitor

@monitor
def training_loop(args, model, device, train_loader, test_loader, optimizer, scheduler):
    for epoch in range(1, args.epochs + 1):
        train(args, model, device, train_loader, optimizer, epoch)
        test(model, device, test_loader)
        scheduler.step()

```

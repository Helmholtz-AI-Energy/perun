# WIP: Perun + MLFlow + Live monitoring callback

By creating a function capable of initializing an MLFlow context that can get passed to the monitoring subprocess, raw perun data can be passed to MLFlow during training.

The files here show an example of this with a very simple scikit learn model.

## How to run

1) Install the dependencies on the `requirenments.txt` file

2) Start a MLFlow server

3) Start the application with the command

```console
MLFLOW_TRACKING_URI="<https://your.mlflow.server:12345>" perun monitor --live_callback_files perun_callback.py -- train_live.py
```

# perun + MLFLow

If you are already using monitoring tools like MLFlow, you might want to add the data collected by perun to enhance the already existing data. This can be done easily with the ```@register_callback``` decorator. An example is shown in the train.py file:

```python
    @register_callback
    def perun2mlflow(node):
        mlflow.start_run(active_run.info.run_id)
        for metricType, metric in node.metrics.items():
            name = f"{metricType.value}"
            mlflow.log_metric(name, metric.value)
```

Functions decorated by ```@register_callback``` takes only one argument, ```node```. The node object is an instance of ```perun.data_model.data.DataNode```, which is a tree structure that contains all the data collected while monitoring the current script. Each node contains the accumulated data of the sub-nodes in the ```metrics``` dictionary. Each metric object contains all the metadata relevant to the value and the value itself. In the example above, the summarized values for power, energy and hardware utilization are being submitted as metrics to the mlflow tracking system.

For more information on the data node object, [check our docs](https://perun.readthedocs.io/en/latest/data.html)

import perun
import os

class perun2mlflow():

    def __init__(self):
        self._activated = False

    def __call__(self):
        self._activated = True
        import platform
        import mlflow
        import os
        hostname = platform.node()

        print(f"In callback: {hostname}")
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment("perun-live-monitoring")

        mlflow.start_run(log_system_metrics=True)

        def func(values):
            """
            Function to log metrics to MLflow.
            """
            mlflow.log_metrics(values, synchronous=False)
        return func

    def __del__(self):
        if self._activated:
            import mlflow
            print("Closing run!")
            mlflow.end_run()

perun.register_live_callback(perun2mlflow(), "mlflow_callback")

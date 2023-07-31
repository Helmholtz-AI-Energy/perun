"""Decorator module."""

# import functools
#
# from perun import config, log
# from perun.configuration import read_custom_config, read_environ, save_to_config
# from perun.perun import Perun
#
#
# def monitor(
#     configuration: str = "./.perun.ini",
#     **conf_kwargs,
# ):
#     """Decorate function to monitor its energy usage.
#
#     Parameters
#     ----------
#     configuration : str, optional
#         Path to configuration file, by default "./.perun.ini"
#
#     Returns
#     -------
#     _type_
#         Function with perun monitoring enabled
#     """
#
#     def inner_function(func):
#         @functools.wraps(func)
#         def func_wrapper(*args, **kwargs):
#             # Get custom config and kwargs
#
#             read_environ()
#
#             read_custom_config(None, None, configuration)
#             for key, value in conf_kwargs.items():
#                 save_to_config(key, value)
#
#             log.setLevel(f"{config.get('debug', 'log_lvl')}")
#
#             perun = Perun(config)
#
#             func_result = perun.monitor_application(func, args, kwargs)
#
#             return func_result
#
#         return func_wrapper
#
#     return inner_function
#

.. _data:

Data
====

perun structures the data collected as a tree, with the root node containing the aggregated data of an indiviudal run of the application, and the nodes further down the tree contain the information of the indivdual compute nodes, devices and *sensors*. *Sensors* are meant as the individual API that perun uses to gather measurements, and a single API can provide information about multiple devices, and multiple devices can be monitored from multiple APIs.

.. image:: images/data_structure.png

Each node in the data structure, once the raw data at the bottom has been processed, contain a set of summarized metrics based on the data that was collected by its sub-nodes, and a metadata dictionary with any information that could be obtained by the application, node, device or API.

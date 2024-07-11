.. Quare documentation master file, created by
   sphinx-quickstart on Wed Jun 26 10:59:37 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Quare's documentation!
=================================

QUality AnalyzeR of application Efficiency

In Latin, "quare" means therefore, because of this, why, in connection with this.

The purpose of the application is to answer the question, based on data from profilers,
why a given application is characterized by a specific performance.



Currently there are three steps of data processing:

- Profile files preprocessing (`csvize.py`)
- Loading profile files to a database (`create_db.py`)
- Data from DB processing and producing plots and data files (`plot.py`)



To properly generate docs use `generate_docs.sh` script from, run from the top project lvl.



.. toctree::
   :maxdepth: 0
   :caption: Contents:

   build/modules



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

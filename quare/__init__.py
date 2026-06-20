"""
Quare — QUality AnalyzeR of application Efficiency.

A framework for ingesting, storing, and visualising performance-profiling data
from HPC applications.  The three-step pipeline is:

1. ``quare preprocess-data`` — normalise raw profiler CSV output
2. ``quare create-db``       — load into a SQLite database
3. ``quare plot``            — generate plots, CSV exports, and INFO tables
"""

__version__ = "0.1.0"

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

# Project root (Quare/) is two levels above docs/source/
sys.path.insert(0, os.path.abspath("../.."))

project = "Quare"
copyright = "2024-2026, Poznań Supercomputing and Networking Center (PSNC)"
author = "Marcin Lawenda"
release = "0.1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_templates"]
autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

# Stub out heavy runtime dependencies so autodoc can import source modules
# without a full package install.
autodoc_mock_imports = [
    "sqlalchemy",
    "pandas",
    "numpy",
    "matplotlib",
]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Typehints settings
typehints_fully_qualified = False
typehints_document_rtype = True

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
sys.path.insert(0, os.path.abspath('../../src/'))


project = 'Quare'
copyright = '2024, PSNC'
author = 'PSNC'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx_autodoc_typehints',
    # 'sphinx.ext.viewcode',
    # 'sphinx.ext.napoleon'
]

templates_path = ['_templates']
exclude_patterns = []
autosummary_generate = True
numpydoc_show_class_members = False



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']



# Typehints settings
typehints_fully_qualified = True
typehints_document_rtype = True



# Hook to add headers to each module
def autodoc_process_docstring(app, what, name, obj, options, lines):
    if what == "module":
        lines.insert(0, name)
        lines.insert(1, "=========================================")


def setup(app):
    app.connect("autodoc-process-docstring", autodoc_process_docstring)

#!/bin/bash
set -e

# Add local Python scripts to PATH (pip install --user installs here)
export PATH="$HOME/.local/bin:$PATH"

rm -rf docs/build docs/source/build
export SPHINX_APIDOC_OPTIONS=members,show-inheritance,private-members
sphinx-apidoc --private -o docs/source/build quare/
pyreverse -o png -p quare -d docs/source/build -A --colorized quare
sphinx-build -M html docs/source docs/build

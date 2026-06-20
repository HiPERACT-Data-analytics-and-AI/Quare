#!/bin/bash
set -e

# Install Python dependencies (runtime + dev group including pylint/pyreverse)
poetry install

# graphviz must be a system package — no pip equivalent; needed by pyreverse
# for UML class/package diagram generation in generate_docs.sh
sudo apt install graphviz -y

#!/bin/bash

rm -r docs/build
rm -r docs/source/build
export SPHINX_APIDOC_OPTIONS=members,show-inheritance,private-members
sphinx-apidoc --private -o docs/source/build src/
sphinx-build -M html docs/source docs/build

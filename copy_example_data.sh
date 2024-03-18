#!/bin/zsh

# thanks to /./ the top most path part is delimited:
rsync --relative .././Cache-impact-on-OpenFOAM/**/*.csv data/
rm -r data/**/old

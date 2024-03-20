#!/bin/zsh

# thanks to /./ the top most path part is delimited:
rsync --relative .././Cache-impact-on-OpenFOAM/**/*.csv raw_data/
rm -r raw_data/**/old

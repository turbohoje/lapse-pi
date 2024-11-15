#!/usr/bin/bash

for ((i=16; i>=1; i--))
do
  echo ""
  echo "./mklapse.sh --days=$i"
  ./mklapse.sh --days=$i
done

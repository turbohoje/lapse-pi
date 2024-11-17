#!/usr/bin/bash

DAYS=10
set -e

for ((i=$DAYS; i>=1; i--))
do
  echo ""
  echo "./mklapse.sh --days=$i"
  ./mklapse.sh --days=$i
done

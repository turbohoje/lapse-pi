#!/usr/bin/bash

DAYS=7

set -e

for ((i=$DAYS; i>=1; i--))
do
  echo ""
  echo "./mklapse.sh --days=$i"
  sleep 2
  ./mklapse.sh --days=$i
  #./mklapse.sh --cam=1 --gcs=1 --upload=0 --gen=1 --days=$i
done

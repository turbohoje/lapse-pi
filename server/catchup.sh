#!/usr/bin/bash

DAYS=5

set -e

for ((i=$DAYS; i>=1; i--))
do
  echo ""
  echo "./cron.sh --days=$i"
  sleep 2
  ./cron.sh --days=$i
  #./mklapse.sh --cam=1 --gcs=1 --upload=0 --gen=1 --days=$i
done

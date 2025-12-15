#!/usr/bin/bash

# continue on fail
set +e

DAYS=1

for arg in "$@"; do
  case $arg in
    --days=*)
      DAYS="${arg#*=}"
      ;;
    *)
      ;;
  esac
done

#timelapse upload

#25 02 * * * /home/turbohoje/lapse-pi/refresh.py > /home/turbohoje/lapse-pi/cron.out 2>&1
/home/turbohoje/lapse-pi/mklapse.sh --days=$DAYS > /home/turbohoje/lapse-pi/cron.out 2>&1

#box/driveway cam/south/hemi
/home/turbohoje/lapse-pi/mklapse.sh --days=$DAYS --cam=1 --gcs=1 --upload=0 --gen=1 --thumb=1 > /home/turbohoje/lapse-pi/cron.out 2>&1
/home/turbohoje/lapse-pi/mklapse.sh --days=$DAYS --cam=2 --gcs=1 --upload=0 --gen=1 --thumb=1 >> /home/turbohoje/lapse-pi/cron.out 2>&1
/home/turbohoje/lapse-pi/mklapse.sh --days=$DAYS --cam=3 --gcs=1 --upload=0 --gen=1 --thumb=1 >> /home/turbohoje/lapse-pi/cron.out 2>&1

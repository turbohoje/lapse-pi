#!/bin/bash

BASEPATH="/home/pi/lapse-pi/archive"
DATE=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d_%H:%M:%S")

mkdir -p "${BASEPATH}/${DATE}/"

/usr/bin/raspistill -o "${BASEPATH}/${DATE}/${TIMESTAMP}.jpg"

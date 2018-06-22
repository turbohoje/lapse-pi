#!/bin/bash

BASEPATH="/home/pi/lapse-pi"
DATE=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d_%H:%M:%S")


mkdir -p "${BASEPATH}/archive/0/${DATE}/"
mkdir -p "${BASEPATH}/processed/0/${DATE}/"


#native cam 0
/usr/bin/raspistill -o "${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg"

mogrify -resize 1280x720^ -gravity south -crop 1280x650+0+0 +repage -write ${BASEPATH}/processed/0/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg


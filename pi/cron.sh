#!/bin/bash

#UN an PW should be set via cron
BASEPATH="/home/turbohoje/lapse-pi"
DATE=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d_%H:%M:%S")

date > ${BASEPATH}/processed/df.txt
df -h >> ${BASEPATH}/processed/df.txt

mkdir -p "${BASEPATH}/archive/0/${DATE}/"
#mkdir -p "${BASEPATH}/processed/0/${DATE}/"

#mkdir -p "${BASEPATH}/archive/1/${DATE}/"
#mkdir -p "${BASEPATH}/processed/1/${DATE}/"

#native cam 0
#/usr/bin/raspistill -o "${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg"


#mogrify -resize 1280x720^ -gravity south -crop 1280x650+0+0 +repage -write ${BASEPATH}/processed/0/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg

#usb cam 1
#fswebcam -r 1280x720 --jpeg 100 -D 16 ${BASEPATH}/archive/1/${DATE}/${TIMESTAMP}.jpg

#mogrify -resize 1280x720^ -gravity south +repage -write ${BASEPATH}/processed/1/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/archive/1/${DATE}/${TIMESTAMP}.jpg

#camera 0, wide angel of the house
curl "https://10.42.0.19/cgi-bin/api.cgi?cmd=Snap&channel=0&user=$UN&password=$PW" -s --insecure --output ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg

/usr/bin/mogrify -compress JPEG2000 -quality 90 -write ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg



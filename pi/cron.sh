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

#camera 0, wide angle of the house
curl "https://10.42.0.19/cgi-bin/api.cgi?cmd=Snap&channel=0&user=$UN&password=$PW" -s --insecure --output ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg

# note: ubuntu/rasbian mogrify does not modify the source file, -write is obeyed.  rocky 9.2 mogrify modifies the source
#/usr/bin/mogrify -compress JPEG2000 -quality 90 -write ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg
#/usr/bin/mogrify -compress JPEG2000 -resize "20%" -write ${BASEPATH}/thumb.jpg ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg

# rocky mogrify
cp ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/src.jpg
#snow
#/home/turbohoje/lapse-pi/pi/snow.py --image1=${BASEPATH}/src.jpg

cp ${BASEPATH}/src.jpg ${BASEPATH}/thumb.jpg
/usr/bin/mogrify -compress JPEG2000 -quality 90   ${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg
/usr/bin/mogrify -compress JPEG2000 -resize "20%" ${BASEPATH}/thumb.jpg 

gsutil cp ${BASEPATH}/src.jpg  gs://tlco-public/latest.jpg
gsutil cp ${BASEPATH}/thumb.jpg  gs://tlco-public/thumb.jpg


#2nd cam
mkdir -p "${BASEPATH}/archive/1/${DATE}/"
curl "https://10.42.0.35/cgi-bin/api.cgi?cmd=Snap&channel=0&user=$UN&password=$PW" -s --insecure --output ${BASEPATH}/archive/1/${DATE}/${TIMESTAMP}.jpg
/usr/bin/mogrify -compress JPEG2000 -quality 90   ${BASEPATH}/archive/1/${DATE}/${TIMESTAMP}.jpg
cp ${BASEPATH}/archive/1/${DATE}/${TIMESTAMP}.jpg ${BASEPATH}/box.jpg

#snow
#/home/turbohoje/lapse-pi/pi/snow.py --image2=${BASEPATH}/box.jpg
gsutil cp ${BASEPATH}/box.jpg  gs://tlco-public/box.jpg

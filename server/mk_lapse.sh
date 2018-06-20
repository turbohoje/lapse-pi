#!/bin/bash

#apt get ffmpeg imagemagick

IMGDIR=~/lapse-pi/archive/
OUTDIR=~/lapse-pi/video-out/imgcache
BAKDIR=/mnt/terra/media/marmot/archive

rsync -azvh --no-o --no-g ${IMGDIR} ${BAKDIR}

MAX=$((60*12))
rm -rf ${OUTDIR}

mkdir -p ${OUTDIR}

trap ctrl_c INT

function ctrl_c() {
        echo "** Trapped CTRL-C"
	exit;
}

COUNT=1
TOTAL=`find ${IMGDIR} -name "*.jpg" | tail -${MAX} | wc -l`
for FILE in `find ${IMGDIR} -name "*.jpg" | sort | tail -${MAX} `; do \
  	echo "Processing file ${COUNT}/${TOTAL}"
	FILENAME=$(printf 'G%07d.JPG' $COUNT)
	mogrify -resize 1280x720^ -gravity south -crop 1280x650+0+0 +repage -write ${OUTDIR}/${FILENAME} $FILE
	COUNT=$((COUNT+1))
done

cd ${OUTDIR}
ffmpeg -start_number 1 -i G%07d.JPG -c:v libx264 -pix_fmt yuv420p video.mp4

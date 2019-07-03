#!/bin/bash

#apt get ffmpeg imagemagick

# crontab
# 0 * * * * run-one /home/turbohoje/lapse-pi/server/mk_lapse.sh

IMGDIR=~/lapse-pi/processed/0
OUTDIR=~/lapse-pi/video-out/imgcache
VIDDIR=~/lapse-pi/video-out
BAKDIR=/mnt/terra/media/marmot/archive

#rsync -azvh --no-o --no-g ${IMGDIR} ${BAKDIR}

MAX=$((60*24))
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
	#mogrify -resize 1280x720^ -gravity south -crop 1280x650+0+0 +repage -write ${OUTDIR}/${FILENAME} $FILE
	cp $FILE ${OUTDIR}/${FILENAME}
	if [[ $? == 0 ]]; then
		COUNT=$((COUNT+1))
	fi
done

cd ${OUTDIR}

rm -f ${VIDDIR}/video.mp4
ffmpeg -start_number 1 -i G%07d.JPG -c:v libx264 -pix_fmt yuv420p ${VIDDIR}/video.mp4
mv ${VIDDIR}/video.mp4 ${VIDDIR}/last.mp4

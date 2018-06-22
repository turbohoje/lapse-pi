#!/bin/bash

CAM=0

BASEPATH="/home/pi/lapse-pi/archive/${CAM}"


#mkdir -p "${BASEPATH}/archive/${CAM}/${DATE}/"
#mkdir -p "${BASEPATH}/processed/${CAM}/${DATE}/"


for FILE in `find ${BASEPATH} | sort`; do
	if [ -f $FILE ]; then 
		DEST=${FILE/archive/processed}
		if [ -f $DEST ]; then
			echo "SKIPPING $DEST"
		else
			DIR=${DEST:0:40}
			if [ ! -d "$DIR" ]; then
				echo "Making ${DIR}"
				mkdir -p ${DIR}
			fi
			echo "Processing $DEST"
			mogrify -resize 1280x720^ -gravity south -crop 1280x650+0+0 +repage -write $DEST $FILE
		fi
	fi
done

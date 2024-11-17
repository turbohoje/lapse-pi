#!/bin/bash
days=1 # number of days since today, 1 == yesterday
gen=1  # 1 == generate file
cam=0  # 0 main hous, 1 box
upload=1

# Parse command-line arguments
for arg in "$@"; do
  case $arg in
    --days=*)
      days="${arg#*=}"
      shift
      ;;
  esac

#   case "--skip"
# 		echo "skiping generation of file"
# 		gen=0
# 	esac
done
echo "Days ago: $days"

#apt get ffmpeg imagemagick

# crontab
# 0 * * * * run-one /home/turbohoje/lapse-pi/server/mk_lapse.sh


DATE=$(date -d "$days day ago" '+%Y-%m-%d')
echo "processing for $DATE"
IMGDIR=~/lapse-pi/archive/$cam/$DATE
OUTDIR=~/lapse-pi/video-out/imgcache$cam
VIDDIR=~/lapse-pi/video-out
#BAKDIR=/mnt/terra/media/marmot/archive
#rsync -azvh --no-o --no-g ${IMGDIR} ${BAKDIR}


if [ $gen == 1 ]; then
	echo "generating video"
	MAX=$((60*24))
	rm -rf ${OUTDIR}
	#rm -rf ${VIDDIR}

	mkdir -p ${OUTDIR}

	trap ctrl_c INT

	function ctrl_c() {
			echo "** Trapped CTRL-C"
		exit;
	}

	COUNT=1
	TOTAL=`find ${IMGDIR} -name "*.jpg" | tail -${MAX} | wc -l`

	for FILE in `find ${IMGDIR} -name "*.jpg"  | sort | tail -${MAX} `; do \
		echo -n "Processing file ${COUNT}/${TOTAL}"
		identify $FILE &> /dev/null;
		if [[ $? -ne 0 ]]; then
				echo " bad img $FILE"
			continue;
		else
			echo " done"
		fi
		
		FILENAME=$(printf 'G%07d.JPG' $COUNT)
		#mogrify -resize 1280x720^ -gravity south -crop 1280x650+0+0 +repage -write ${OUTDIR}/${FILENAME} $FILE
		cp $FILE ${OUTDIR}/${FILENAME}
		if [[ $? == 0 ]]; then
			COUNT=$((COUNT+1))
		fi
	done



	#make the video
	set -x
	cd ${OUTDIR}
	rm -f $VIDDIR/video.mp4
	echo "generating video for $DATE"
	ffmpeg -start_number 1 -i G%07d.JPG -c:v libx264 -pix_fmt yuv420p ${VIDDIR}/video.mp4
	mv $VIDDIR/video.mp4 $VIDDIR/last.mp4
	set +x
fi

set -x
if [ $upload == 1 ]; then
	cd /home/turbohoje/lapse-pi/
	echo "token"
	./refresh.py
	echo "uploading video"
	./up.py $DATE
else
	mv $VIDDIR/last.mp4 $VIDDIR/$DATE-$cam.mp4
	ls -hal $VIDDIR/*.mp4
fi
set +x
#./mklapse.sh --days=$days --cam=1


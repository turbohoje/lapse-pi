#!/bin/bash

#UN an PW should be set via cron
BASEPATH="/home/turbohoje/lapse-pi"
DATE=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d_%H:%M:%S")

is_valid_jpeg() {
    [[ -f "$1" ]] && file "$1" | grep -q "JPEG"
}

date > ${BASEPATH}/processed/df.txt
df -h >> ${BASEPATH}/processed/df.txt

#camera 0, wide angle of the house
mkdir -p "${BASEPATH}/archive/0/${DATE}/"
SNAP0="${BASEPATH}/archive/0/${DATE}/${TIMESTAMP}.jpg"
curl "https://10.42.0.19/cgi-bin/api.cgi?cmd=Snap&channel=0&user=$UN&password=$PW" -s --insecure --output "$SNAP0"
if is_valid_jpeg "$SNAP0"; then
    # note: ubuntu/rasbian mogrify does not modify the source file, -write is obeyed.  rocky 9.2 mogrify modifies the source
    cp "$SNAP0" ${BASEPATH}/src.jpg
    cp ${BASEPATH}/src.jpg ${BASEPATH}/thumb.jpg
    /usr/bin/mogrify -compress JPEG2000 -quality 90   "$SNAP0"
    /usr/bin/mogrify -compress JPEG2000 -resize "20%" ${BASEPATH}/thumb.jpg
    rclone copyto ${BASEPATH}/src.jpg   r2:marmot/latest.jpg
    rclone copyto ${BASEPATH}/thumb.jpg r2:marmot/thumb.jpg
else
    echo "cam0: fetch failed or invalid image, skipping"
    rm -f "$SNAP0"
fi

#2nd cam
mkdir -p "${BASEPATH}/archive/1/${DATE}/"
SNAP1="${BASEPATH}/archive/1/${DATE}/${TIMESTAMP}.jpg"
curl "https://10.42.0.67/cgi-bin/api.cgi?cmd=Snap&channel=0&user=$UN&password=$PW" -s --insecure --output "$SNAP1"
if is_valid_jpeg "$SNAP1"; then
    /usr/bin/mogrify -compress JPEG2000 -quality 90 "$SNAP1"
    cp "$SNAP1" ${BASEPATH}/box.jpg
    rclone copyto ${BASEPATH}/box.jpg r2:marmot/box.jpg
else
    echo "cam1: fetch failed or invalid image, skipping"
    rm -f "$SNAP1"
fi

#3rd cam 10.42.0.94
mkdir -p "${BASEPATH}/archive/2/${DATE}/"
SNAP2="${BASEPATH}/archive/2/${DATE}/${TIMESTAMP}.jpg"
curl "https://10.42.0.94/cgi-bin/api.cgi?cmd=Snap&channel=0&user=admin&password=$PW" -s --insecure --output "$SNAP2"
if is_valid_jpeg "$SNAP2"; then
    /usr/bin/mogrify -compress JPEG2000 -quality 90 "$SNAP2"
    cp "$SNAP2" ${BASEPATH}/south.jpg
    rclone copyto ${BASEPATH}/south.jpg r2:marmot/south.jpg

    #crop
    left=1986
    right=3840
    rr=$(( right - left ))
    mogrify -crop ${left}x0+${rr}+0 +repage -path . -format jpg -write ${BASEPATH}/bg.jpg ${BASEPATH}/south.jpg
    # Add date/time watermark at bottom center
    convert "${BASEPATH}/bg.jpg" \
      -gravity southeast \
      -pointsize 24 \
      -fill "rgba(200,200,200,0.9)" \
      -annotate +20+20 "$(date '+%Y-%m-%d %H:%M:%S')" \
      "${BASEPATH}/bg.jpg"

    echo "uploading to website"
    scp ${BASEPATH}/bg.jpg turbohoje@tlwebsite:/var/www/html/img/bg.jpg
    rclone copyto ${BASEPATH}/bg.jpg r2:/img/bg.jpg
else
    echo "cam2: fetch failed or invalid image, skipping"
    rm -f "$SNAP2"
fi

#4th cam
mkdir -p "${BASEPATH}/archive/3/${DATE}/"
SNAP3="${BASEPATH}/archive/3/${DATE}/${TIMESTAMP}.jpg"
curl "https://10.42.0.95/cgi-bin/api.cgi?cmd=Snap&channel=0&user=admin&password=$PW" -s --insecure --output "$SNAP3"
if is_valid_jpeg "$SNAP3"; then
    /usr/bin/mogrify -compress JPEG2000 -quality 90 "$SNAP3"
    cp "$SNAP3" ${BASEPATH}/uphemi.jpg
    rclone copyto ${BASEPATH}/uphemi.jpg r2:marmot/uphemi.jpg
else
    echo "cam3: fetch failed or invalid image, skipping"
    rm -f "$SNAP3"
fi

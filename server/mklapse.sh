#!/bin/bash
days=1 # number of days since today, 1 == yesterday
gen=1  # 1 == generate file
cam=0  # 0 main hous, 1 box
upload=1 #upload to yt
gcs=0 # upload weekday to bucket
thumb=0 # 1 == update combined thumbnail sprite

# Parse command-line arguments
for arg in "$@"; do
  case $arg in
    --days=*)
      days="${arg#*=}"
      shift
      ;;
    --gen=*)
      gen="${arg#*=}"
      shift
      ;;
    --cam=*)
      cam="${arg#*=}"
      shift
      ;;
    --upload=*)
      upload="${arg#*=}"
      shift
      ;;
    --gcs=*)
      gcs="${arg#*=}"
      shift
      ;;
    --thumb=*)
      thumb="${arg#*=}"
      shift
      ;;
    --skip)
      echo "Skipping generation of file"
      gen=0
      shift
      ;;
    *)
      echo "Unknown argument: $arg"
      ;;
  esac
done

echo "Days ago: $days"
echo "Generate file: $gen"
echo "Camera type: $cam"
echo "Upload YT: $upload"
echo "GCS upload: $gcs"
echo "Update thumbnail sprite: $thumb"

# crontab (for reference)
# 0  3 * * * /home/turbohoje/lapse-pi/mklapse.sh --cam=1 --gcs=1 --upload=0 --gen=1 --thumb=1 > /home/turbohoje/lapse-pi/boxcron.out 2>&1
# 0  4 * * * /home/turbohoje/lapse-pi/mklapse.sh --cam=2 --gcs=1 --upload=0 --gen=1 --thumb=1 > /home/turbohoje/lapse-pi/boxcron.out 2>&1
# 0  5 * * * /home/turbohoje/lapse-pi/mklapse.sh --cam=3 --gcs=1 --upload=0 --gen=1 --thumb=1 > /home/turbohoje/lapse-pi/boxcron.out 2>&1

DATE=$(date -d "$days day ago" '+%Y-%m-%d')
DOW=$(date -d "$days day ago" +"%A")
echo "processing for $DATE $DOW"
sleep 2

IMGDIR=~/lapse-pi/archive/$cam/$DATE
OUTDIR=~/lapse-pi/video-out/imgcache$cam
VIDDIR=~/lapse-pi/video-out
SPRITE=${VIDDIR}/thumb-sprite.png

# Thumb layout settings
# These are *cell* sizes for the sprite, independent of the camera native size.
# You can tune these if you want larger/smaller thumbs.
THUMB_W=320
THUMB_H=180
SPRITE_COLS=7   # Sun..Sat
SPRITE_ROWS=3   # cams 1..3
SPRITE_W=$((THUMB_W * SPRITE_COLS))
SPRITE_H=$((THUMB_H * SPRITE_ROWS))

if [ $gen == 1 ]; then
  echo "Generating video in ${OUTDIR} from images in ${IMGDIR}"
  MAX=$((60*24))
  rm -rf ${OUTDIR}
  mkdir -p ${OUTDIR}

  trap ctrl_c INT
  function ctrl_c() {
    echo "** Trapped CTRL-C"
    exit;
  }

  COUNT=1
  TOTAL=$(find "${IMGDIR}" -name "*.jpg" | tail -"${MAX}" | wc -l)

  for FILE in $(find "${IMGDIR}" -name "*.jpg" | sort | tail -"${MAX}"); do
    echo -n "Processing file ${COUNT}/${TOTAL}"
    identify "$FILE" &> /dev/null
    if [[ $? -ne 0 ]]; then
      echo " bad img $FILE"
      continue
    else
      echo " done"
    fi

    FILENAME=$(printf 'G%07d.JPG' "$COUNT")
    # Here you *could* normalize resolution if you want, but for now we just copy.
    cp "$FILE" "${OUTDIR}/${FILENAME}"
    if [[ $? == 0 ]]; then
      COUNT=$((COUNT+1))
    fi
  done

  # make the video
  set -x
  cd "${OUTDIR}"
  rm -f "${VIDDIR}/video.mp4"
  echo "generating video for $DATE"
  ffmpeg -start_number 1 -i G%07d.JPG -c:v libx264 -pix_fmt yuv420p "${VIDDIR}/video.mp4"
  mv "${VIDDIR}/video.mp4" "${VIDDIR}/last.mp4"
  set +x
fi

# Helper: generate/update combined thumbnail sprite
update_thumb_sprite() {
  # need some frames to pick from
  if [ ! -d "${OUTDIR}" ]; then
    echo "Thumbnail sprite: OUTDIR ${OUTDIR} does not exist, skipping thumb update."
    return
  fi

  local frame_count
  frame_count=$(ls "${OUTDIR}"/G*.JPG 2>/dev/null | wc -l)
  if [ "$frame_count" -eq 0 ]; then
    echo "Thumbnail sprite: no frames found in ${OUTDIR}, skipping."
    return
  fi

  # pick a frame roughly from the middle of the day
  local mid_idx=$((frame_count / 2))
  if [ "$mid_idx" -lt 1 ]; then
    mid_idx=1
  fi
  local mid_frame
  mid_frame=$(printf 'G%07d.JPG' "$mid_idx")
  local src_path="${OUTDIR}/${mid_frame}"

  if [ ! -f "$src_path" ]; then
    echo "Thumbnail sprite: mid frame ${src_path} not found, skipping."
    return
  fi

  # map DOW -> column index (0 = Sunday)
  local day_index
  case "$DOW" in
    Sunday)    day_index=0 ;;
    Monday)    day_index=1 ;;
    Tuesday)   day_index=2 ;;
    Wednesday) day_index=3 ;;
    Thursday)  day_index=4 ;;
    Friday)    day_index=5 ;;
    Saturday)  day_index=6 ;;
    *)
      echo "Unknown DOW: $DOW, skipping thumb update."
      return ;;
  esac

  # cam index (1..3) to row index (0..2)
  local row_index=$((cam - 1))
  if [ "$row_index" -lt 0 ] || [ "$row_index" -ge "$SPRITE_ROWS" ]; then
    echo "Unexpected cam index $cam for sprite rows, skipping thumb update."
    return
  fi

  local offset_x=$((day_index * THUMB_W))
  local offset_y=$((row_index * THUMB_H))

  echo "Thumbnail sprite: updating cam=${cam}, DOW=${DOW} (col=${day_index}), offsets x=${offset_x}, y=${offset_y}"

  mkdir -p "${VIDDIR}"

  # Create blank sprite if needed
  if [ ! -f "${SPRITE}" ]; then
    echo "Thumbnail sprite: creating new blank sprite ${SPRITE} (${SPRITE_W}x${SPRITE_H})"
    # black background; change to 'xc:#000000' or another color if you prefer
    convert -size "${SPRITE_W}x${SPRITE_H}" xc:black "${SPRITE}"
  fi

  # Create resized/padded thumb from the chosen frame
  # IMPORTANT CHANGE: we *fit* within THUMB_WxTHUMB_H and pad, so different camera dimensions are handled.
  local tmp_thumb="${VIDDIR}/thumb_tmp_${cam}_${DOW}.jpg"
  convert "${src_path}" \
    -resize "${THUMB_W}x${THUMB_H}" \
    -gravity center \
    -background black \
    -extent "${THUMB_W}x${THUMB_H}" \
    "${tmp_thumb}"

  # Composite into sprite at the correct position
  convert "${SPRITE}" "${tmp_thumb}" \
    -geometry +${offset_x}+${offset_y} \
    -compose over -composite "${SPRITE}"

  rm -f "${tmp_thumb}"

  # Upload sprite to GCS (single shared file)
  #gsutil cp "${SPRITE}" gs://tlco-public/thumbs.png
  rclone copyto "${SPRITE}" r2:/marmot/thumbs.png  
}

set -x
if [ $upload == 1 ]; then
  cd /home/turbohoje/lapse-pi/
  echo "refreshing yt token via script"
  ./refresh.py
  echo "uploading video to yt via script"
  ./up.py $DATE
else
  mv "${VIDDIR}/last.mp4" "${VIDDIR}/${DATE}-${cam}.mp4"

  if [ $gcs == 1 ]; then
    #gsutil cp "${VIDDIR}/${DATE}-${cam}.mp4" gs://tlco-public/${cam}_$DOW.mp4
    rclone copyto "${VIDDIR}/${DATE}-${cam}.mp4" r2:/marmot/${cam}_$DOW.mp4
  fi
fi
set +x

# Only after video generation & (optionally) GCS video upload, update sprite if requested
if [ "$thumb" == "1" ]; then
  echo "Updating combined thumbnail sprite..."
  update_thumb_sprite
fi

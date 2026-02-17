#!/usr/bin/env python3
"""
noon-lapse.py - Build a timelapse video from daily solar-noon snapshots (camera 0).

Connects to the remote lapse-pi archive on the Synology NAS, computes
celestial (solar) noon for each date, finds the closest image, downloads
them via rsync, and stitches them into an MP4 with ffmpeg.

Solar noon accounts for:
  - Colorado DST observance (MDT Mar-Nov adds ~1 hr to clock time)
  - Equation of Time (Earth's orbital eccentricity, +/- 16 min seasonal)
  - Longitude offset from the 105 W timezone meridian (Telluride = 107.81 W)

Usage:
    python3 noon-lapse.py [--start=YYYY-MM-DD] [--end=YYYY-MM-DD] [--fps=N]
                          [--longitude=DEG_WEST] [--dry-run] [--skip-download]
"""

import subprocess
import sys
import os
import re
import math
from datetime import date
from collections import defaultdict

REMOTE = "turbohoje@10.22.14.3"
REMOTE_BASE = "/var/services/homes/turbohoje/lapse-pi/archive/0"
DEFAULT_LONGITUDE_WEST = 107.81  # Telluride, CO
TIMEZONE_MERIDIAN = 105.0        # Mountain Time standard meridian


# ---------------------------------------------------------------------------
# Solar-noon helpers
# ---------------------------------------------------------------------------

def is_dst(d):
    """True if date d falls within US DST (2nd Sunday of March to 1st Sunday of November)."""
    year = d.year

    # 2nd Sunday of March
    mar1_dow = date(year, 3, 1).weekday()          # Mon=0 .. Sun=6
    first_sun_mar = 1 + (6 - mar1_dow) % 7
    dst_start = date(year, 3, first_sun_mar + 7)

    # 1st Sunday of November
    nov1_dow = date(year, 11, 1).weekday()
    first_sun_nov = 1 + (6 - nov1_dow) % 7
    dst_end = date(year, 11, first_sun_nov)

    return dst_start <= d < dst_end


def equation_of_time(d):
    """Equation of Time in minutes (Spencer 1971 approximation).

    Positive => sundial is ahead of mean clock, so solar noon is *earlier*
    than 12:00 mean solar time.
    """
    n = d.timetuple().tm_yday
    B = math.radians(360.0 / 365.0 * (n - 81))
    return 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)


def solar_noon_minutes(d, longitude_west=DEFAULT_LONGITUDE_WEST):
    """Return solar noon as minutes-from-midnight in local clock time.

    Formula (at the timezone's standard meridian, solar noon = 12:00 mean):
        solar_noon = 720 - EoT + (lng - 105) * 4 + DST_offset
    """
    eot = equation_of_time(d)
    lng_correction = (longitude_west - TIMEZONE_MERIDIAN) * 4.0   # min
    dst_offset = 60 if is_dst(d) else 0
    return 720.0 - eot + lng_correction + dst_offset


def fmt_minutes(m):
    """Format minutes-from-midnight as HH:MM."""
    h = int(m) // 60
    mi = int(m) % 60
    return f"{h:02d}:{mi:02d}"


# ---------------------------------------------------------------------------
# SSH / CLI helpers
# ---------------------------------------------------------------------------

def run_ssh(cmd, timeout=120):
    """Run a command on the remote host and return stdout."""
    result = subprocess.run(
        ["ssh", REMOTE, cmd],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        print(f"SSH error: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout


def parse_args():
    args = {
        "start": None, "end": None, "fps": 15,
        "longitude": DEFAULT_LONGITUDE_WEST, "dry_run": False,
        "skip_download": False,
    }
    for arg in sys.argv[1:]:
        if arg.startswith("--start="):
            args["start"] = arg.split("=", 1)[1]
        elif arg.startswith("--end="):
            args["end"] = arg.split("=", 1)[1]
        elif arg.startswith("--fps="):
            args["fps"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--longitude="):
            args["longitude"] = float(arg.split("=", 1)[1])
        elif arg == "--dry-run":
            args["dry_run"] = True
        elif arg == "--skip-download":
            args["skip_download"] = True
        else:
            print(f"Unknown argument: {arg}")
            print(__doc__)
            sys.exit(1)
    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    lng = args["longitude"]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workdir = os.path.join(script_dir, "noon-lapse-work")
    output = os.path.join(script_dir, "noon-lapse.mp4")

    ts_re = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{2}):(\d{2}):(\d{2})\.jpg$')
    rawdir = os.path.join(workdir, "raw")

    if args["skip_download"]:
        # --- Skip download: build noon_files from already-downloaded images ---
        print("Skipping download, scanning local raw directory...")
        if not os.path.isdir(rawdir):
            print(f"No raw directory found at {rawdir}", file=sys.stderr)
            sys.exit(1)

        by_date = defaultdict(list)
        for d_str in sorted(os.listdir(rawdir)):
            daydir = os.path.join(rawdir, d_str)
            if not os.path.isdir(daydir) or not re.match(r'^\d{4}-\d{2}-\d{2}$', d_str):
                continue
            if args["start"] and d_str < args["start"]:
                continue
            if args["end"] and d_str > args["end"]:
                continue
            for fname in os.listdir(daydir):
                m = ts_re.search(fname)
                if not m:
                    continue
                h, mi, s = int(m.group(2)), int(m.group(3)), int(m.group(4))
                file_min = h * 60 + mi + s / 60.0
                by_date[d_str].append((file_min, f"{d_str}/{fname}"))

        noon_files = []
        for d_str in sorted(by_date):
            y, mo, dy = map(int, d_str.split('-'))
            target = solar_noon_minutes(date(y, mo, dy), lng)
            best_delta = float('inf')
            best_rel = None
            for file_min, relpath in by_date[d_str]:
                delta = abs(file_min - target)
                if delta < best_delta:
                    best_delta = delta
                    best_rel = relpath
            if best_rel:
                noon_files.append((d_str, best_delta, best_rel, target))

        print(f"Found {len(noon_files)} images in local cache")
        if not noon_files:
            print("No images found in raw directory.", file=sys.stderr)
            sys.exit(1)

    else:
        # --- Step 1: grab all files in the 11:xx - 13:xx range in one SSH call ---
        print(f"Scanning remote archive for camera 0 images (hours 11-13)...")
        print(f"  Longitude: {lng:.2f} W  |  Meridian offset: {(lng - TIMEZONE_MERIDIAN) * 4:.1f} min")
        raw = run_ssh(
            f'for d in {REMOTE_BASE}/????-??-??; do '
            f'  ls "$d"/*_11:*.jpg "$d"/*_12:*.jpg "$d"/*_13:*.jpg 2>/dev/null; '
            f'done'
        )

        # Parse into {date: [(file_minutes, relpath), ...]}
        by_date = defaultdict(list)
        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            m = ts_re.search(line)
            if not m:
                continue
            d = m.group(1)
            if args["start"] and d < args["start"]:
                continue
            if args["end"] and d > args["end"]:
                continue
            h, mi, s = int(m.group(2)), int(m.group(3)), int(m.group(4))
            file_min = h * 60 + mi + s / 60.0
            fname = os.path.basename(line)
            by_date[d].append((file_min, f"{d}/{fname}"))

        # --- Step 2: for each date, compute solar noon and pick closest file ---
        noon_map = {}  # date_str -> (delta_min, relpath, solar_noon_min)
        for d_str in sorted(by_date):
            y, mo, dy = map(int, d_str.split('-'))
            target = solar_noon_minutes(date(y, mo, dy), lng)
            best_delta = float('inf')
            best_rel = None
            for file_min, relpath in by_date[d_str]:
                delta = abs(file_min - target)
                if delta < best_delta:
                    best_delta = delta
                    best_rel = relpath
            if best_rel:
                noon_map[d_str] = (best_delta, best_rel, target)

        # --- Step 3: handle dates with no files in the 11-13 range ---
        all_dates_raw = run_ssh(
            f'ls -d {REMOTE_BASE}/????-??-?? 2>/dev/null'
        )
        all_dates = []
        for line in all_dates_raw.strip().split('\n'):
            d = os.path.basename(line.strip())
            if re.match(r'^\d{4}-\d{2}-\d{2}$', d):
                if args["start"] and d < args["start"]:
                    continue
                if args["end"] and d > args["end"]:
                    continue
                all_dates.append(d)

        missing = [d for d in all_dates if d not in noon_map]
        if missing:
            print(f"  {len(missing)} dates missing files near solar noon, scanning fallback...")
            for d_str in missing:
                day_raw = run_ssh(
                    f'ls {REMOTE_BASE}/{d_str}/*.jpg 2>/dev/null', timeout=15
                )
                if not day_raw.strip():
                    print(f"    {d_str}: no images, skipping")
                    continue
                y, mo, dy = map(int, d_str.split('-'))
                target = solar_noon_minutes(date(y, mo, dy), lng)
                best_delta = float('inf')
                best_rel = None
                for fline in day_raw.strip().split('\n'):
                    fline = fline.strip()
                    fm = ts_re.search(fline)
                    if not fm:
                        continue
                    h, mi, s = int(fm.group(2)), int(fm.group(3)), int(fm.group(4))
                    file_min = h * 60 + mi + s / 60.0
                    delta = abs(file_min - target)
                    if delta < best_delta:
                        best_delta = delta
                        best_rel = f"{d_str}/{os.path.basename(fline)}"
                if best_rel:
                    noon_map[d_str] = (best_delta, best_rel, target)
                    print(f"    {d_str}: {best_rel.split('/')[-1]} "
                          f"(solar noon {fmt_minutes(target)}, delta {best_delta:.0f} min)")
                else:
                    print(f"    {d_str}: no valid images, skipping")

        # --- Build sorted result list ---
        noon_files = []
        for d_str in sorted(noon_map):
            delta, relpath, target = noon_map[d_str]
            noon_files.append((d_str, delta, relpath, target))

        print(f"\nFound {len(noon_files)} solar-noon images across {len(all_dates)} total dates")
        if not noon_files:
            print("No images found.", file=sys.stderr)
            sys.exit(1)

        # Show samples
        for d_str, delta, path, target in noon_files[:3]:
            dst_label = "MDT" if is_dst(date(*map(int, d_str.split('-')))) else "MST"
            print(f"  {d_str} ({dst_label}): {path.split('/')[-1]}  "
                  f"solar noon={fmt_minutes(target)}  delta={delta:.0f} min")
        if len(noon_files) > 6:
            print(f"  ...")
            for d_str, delta, path, target in noon_files[-3:]:
                dst_label = "MDT" if is_dst(date(*map(int, d_str.split('-')))) else "MST"
                print(f"  {d_str} ({dst_label}): {path.split('/')[-1]}  "
                      f"solar noon={fmt_minutes(target)}  delta={delta:.0f} min")

        if args["dry_run"]:
            print(f"\n[dry-run] Would download {len(noon_files)} images "
                  f"and generate video at {args['fps']} fps.")
            sys.exit(0)

        # --- Step 4: download via rsync --files-from ---
        os.makedirs(workdir, exist_ok=True)
        os.makedirs(rawdir, exist_ok=True)

        filelist_path = os.path.join(workdir, "noon-files.txt")
        with open(filelist_path, "w") as f:
            for _, _, relpath, _ in noon_files:
                f.write(relpath + "\n")

        print(f"\nDownloading {len(noon_files)} images via rsync...")
        subprocess.run(
            [
                "rsync", "-avz", "--progress",
                f"--files-from={filelist_path}",
                f"{REMOTE}:{REMOTE_BASE}/",
                rawdir + "/",
            ],
            check=True,
            timeout=600,
        )

    # --- Step 5: create numbered symlinks (avoids colons in filenames) ---
    fps = args["fps"]
    framedir = os.path.join(workdir, "frames")
    if os.path.isdir(framedir):
        for f in os.listdir(framedir):
            os.remove(os.path.join(framedir, f))
    else:
        os.makedirs(framedir)

    filelist_path = os.path.join(workdir, "noon-files.txt")
    count = 0
    skipped = 0
    with open(filelist_path, "w") as f:
        for d_str, _, relpath, _ in noon_files:
            src = os.path.abspath(os.path.join(rawdir, relpath))
            if not os.path.exists(src):
                print(f"  Warning: missing {src}, skipping")
                skipped += 1
                continue
            # Validate image with ffprobe before including
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0", src],
                capture_output=True, text=True, timeout=10
            )
            if probe.returncode != 0 or not probe.stdout.strip():
                print(f"  Warning: bad image {relpath}, skipping")
                skipped += 1
                continue
            link = os.path.join(framedir, f"frame{count:05d}.jpg")
            os.symlink(src, link)
            f.write(f"{relpath}\n")
            count += 1
    if skipped:
        print(f"  Skipped {skipped} missing/corrupt images")

    print(f"\n{count} frames ready for encoding")
    if count == 0:
        print("No frames available.", file=sys.stderr)
        sys.exit(1)

    # --- Step 6: write concat file from symlinks and generate video ---
    concatfile = os.path.join(workdir, "concat.txt")
    frame_duration = 1.0 / fps
    with open(concatfile, "w") as cf:
        for i in range(count):
            cf.write(f"file 'frames/frame{i:05d}.jpg'\n")
            cf.write(f"duration {frame_duration:.6f}\n")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concatfile,
        "-c:v", "libx264",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        output,
    ]
    print(f"\nGenerating video at {fps} fps: {output}")
    print(f"  $ {' '.join(ffmpeg_cmd)}")
    subprocess.run(ffmpeg_cmd, check=True, timeout=600)

    duration_sec = count / fps
    print(f"\nDone! {output}")
    print(f"  {count} frames @ {fps} fps = {duration_sec:.1f}s")
    print(f"  Date range: {noon_files[0][0]} to {noon_files[-1][0]}")


if __name__ == "__main__":
    main()

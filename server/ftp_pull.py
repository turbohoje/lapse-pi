#!/usr/bin/env python3
"""
sync_cameras.py

Pulls images from tlwebsite:/home/jmeyer/webform/{box,marmot,south}
to nuchaus:/home/turbohoje/lapse-pi/archive/{1,0,2}

Source filename:  <prefix>_00_YYYYMMDDHHMMSS.jpg
Dest structure:   YYYY-MM-DD/YYYY-MM-DD_HH:MM:SS.jpg

- Transfers per-file via ssh cat, deletes source after confirmed copy
- Skips and deletes .txt files
- Safe to interrupt and re-run
"""

import subprocess
import os
import re
import logging
import sys
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────

REMOTE_HOST   = "tlwebsite"
REMOTE_BASE   = "/home/jmeyer/webform"
LOCAL_BASE    = "/home/turbohoje/lapse-pi/archive"
LOG_FILE      = "/home/turbohoje/sync_cameras.log"

CAMERA_MAP = {
    "marmot": "0",
    "box":    "1",
    "south":  "2",
}

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

TIMESTAMP_RE = re.compile(r'(\d{14})\.jpg$', re.IGNORECASE)

def shell_quote(path):
    """Single-quote a path for safe use in a remote shell command."""
    return "'" + path.replace("'", "'\\''") + "'"

def parse_timestamp(filename):
    m = TIMESTAMP_RE.search(filename)
    if not m:
        return None
    ts = m.group(1)
    try:
        dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
    except ValueError:
        return None

def remote_find(camera_dir):
    """Return list of absolute file paths under the remote camera dir."""
    cmd = ["ssh", REMOTE_HOST, f"find {REMOTE_BASE}/{camera_dir} -type f"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"find failed for {camera_dir}: {result.stderr.strip()}")
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def remote_delete(remote_path):
    """Delete a single file on the remote host."""
    shell_cmd = f"rm -f {shell_quote(remote_path)}"
    log.info(f"  Deleting remote: [{remote_path}]")
    result = subprocess.run(["ssh", REMOTE_HOST, shell_cmd], capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"  Delete failed [{remote_path}]: {result.stderr.strip()}")
        return False
    log.info(f"  Deleted OK: [{remote_path}]")
    return True

def transfer_file(remote_path, local_path):
    """
    Stream file via ssh cat into a local tmp file, then rename.
    Uses shell_quote so spaces in remote paths are handled correctly.
    """
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    tmp_path = local_path + ".tmp"
    shell_cmd = f"cat {shell_quote(remote_path)}"
    with open(tmp_path, "wb") as f:
        result = subprocess.run(["ssh", REMOTE_HOST, shell_cmd], stdout=f, stderr=subprocess.PIPE)
    if result.returncode != 0:
        log.error(f"  transfer failed [{remote_path}]: {result.stderr.decode().strip()}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False
    os.rename(tmp_path, local_path)
    return True

# ─── MAIN ────────────────────────────────────────────────────────────────────

def sync_camera(camera_name, archive_index):
    log.info(f"── Syncing {camera_name} → archive/{archive_index}")
    files = remote_find(camera_name)

    if not files:
        log.info(f"  No files found for {camera_name}")
        return

    transferred = 0
    skipped     = 0
    deleted_txt = 0
    errors      = 0

    for remote_path in files:
        filename = os.path.basename(remote_path)

        # Delete .txt files (Reolink test files)
        if filename.lower().endswith(".txt"):
            log.info(f"  Deleting txt: [{filename}]")
            remote_delete(remote_path)
            deleted_txt += 1
            continue

        # Skip non-jpg
        if not filename.lower().endswith(".jpg"):
            log.warning(f"  Skipping unknown file type: [{filename}]")
            skipped += 1
            continue

        # Parse timestamp
        parsed = parse_timestamp(filename)
        if not parsed:
            log.warning(f"  Could not parse timestamp from: [{filename}], skipping")
            skipped += 1
            continue

        date_str, time_str = parsed
        dest_filename = f"{date_str}_{time_str}.jpg"
        dest_dir      = os.path.join(LOCAL_BASE, archive_index, date_str)
        dest_path     = os.path.join(dest_dir, dest_filename)

        # Already exists — clean up remote and move on
        if os.path.exists(dest_path):
            log.info(f"  Already exists: [{dest_filename}], removing source: [{remote_path}]")
            remote_delete(remote_path)
            continue

        # Transfer
        log.info(f"  {filename} → {dest_path}")
        if not transfer_file(remote_path, dest_path):
            errors += 1
            continue

        # Verify
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            log.error(f"  Verification failed for [{dest_path}], not deleting source")
            errors += 1
            continue

        # Delete source only after confirmed transfer
        if remote_delete(remote_path):
            transferred += 1
        else:
            errors += 1

    log.info(f"  Done: {transferred} transferred, {skipped} skipped, "
             f"{deleted_txt} txt deleted, {errors} errors")

def main():
    log.info("═══ Camera sync start ═══")
    for camera_name, archive_index in CAMERA_MAP.items():
        try:
            sync_camera(camera_name, archive_index)
        except Exception as e:
            log.error(f"Unexpected error syncing {camera_name}: {e}")
    log.info("═══ Camera sync complete ═══")

if __name__ == "__main__":
    main()

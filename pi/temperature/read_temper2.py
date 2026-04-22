#!/usr/bin/env python3
"""Read temperatures from PCsensor TEMPer2 USB thermometer (VID:PID 3553:a001).

Requires access to /dev/hidraw* — either run as root or install the udev rule:
    sudo cp 99-temper2.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules && sudo udevadm trigger
    sudo usermod -aG plugdev $USER   # then log out/in

https://www.amazon.com/dp/B0B7SJVXST?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_7

"""

import os
import select
import struct
import glob
import sys
import time
from datetime import datetime

VENDOR_ID  = 0x3553
PRODUCT_ID = 0xA001

FIRMWARE_QUERY = struct.pack('8B', 0x01, 0x86, 0xff, 0x01, 0, 0, 0, 0)
TEMP_QUERY     = struct.pack('8B', 0x01, 0x80, 0x33, 0x01, 0, 0, 0, 0)


def find_temper2_hidraw():
    """Return the last hidraw path belonging to the TEMPer2 (ccwienk uses [-1])."""
    found = []
    for hidraw_dir in sorted(glob.glob('/sys/class/hidraw/hidraw*')):
        uevent = os.path.join(hidraw_dir, 'device', 'uevent')
        try:
            with open(uevent) as f:
                content = f.read().upper()
            if f'{VENDOR_ID:08X}:{PRODUCT_ID:08X}' in content:
                found.append(f'/dev/{os.path.basename(hidraw_dir)}')
        except OSError:
            pass
    return found


def read_until_timeout(fd, timeout, chunk=8):
    """Read all available data from fd until no more arrives within timeout seconds."""
    data = b''
    while True:
        ready, _, _ = select.select([fd], [], [], timeout)
        if fd not in ready:
            break
        data += os.read(fd, chunk)
    return data


def query_firmware(fd, debug=False):
    """Send firmware query; retry until we get >8 bytes back."""
    for attempt in range(10):
        os.write(fd, FIRMWARE_QUERY)
        firmware = read_until_timeout(fd, timeout=0.2)
        if debug:
            print(f'  firmware attempt {attempt}: {firmware.hex()!r}', file=sys.stderr)
        if len(firmware) > 8:
            return firmware.decode('ascii', errors='replace').strip('\x00').strip()
    return firmware.decode('ascii', errors='replace').strip('\x00').strip()


def query_temperatures(fd, debug=False):
    os.write(fd, TEMP_QUERY)
    data = read_until_timeout(fd, timeout=0.1)
    if debug:
        print(f'  temp raw ({len(data)}B): {data.hex()}  {list(data)}', file=sys.stderr)
    return data


def parse_internal_temp(data, debug=False):
    """Parse internal (USB stick) sensor temperature from bytes 2-3."""
    if len(data) < 4:
        raise ValueError(f'Response too short for internal data: {len(data)} bytes — {data.hex()}')
    return struct.unpack_from('>h', data, 2)[0] / 100.0


def parse_probe_temp(data, debug=False):
    """Parse external probe temperature from bytes 10-11 (bytes 2-3 of second HID report)."""
    if len(data) < 12:
        raise ValueError(f'Response too short for probe data: {len(data)} bytes — {data.hex()}')
    return struct.unpack_from('>h', data, 10)[0] / 100.0


def c_to_f(c):
    return c * 9 / 5 + 32


HDR = f"{'Timestamp':<20}  {'Internal °C':>11}  {'Internal °F':>11}  {'Probe °C':>8}  {'Probe °F':>8}"
SEP = '-' * len(HDR)


def take_reading(path, debug):
    fd = os.open(path, os.O_RDWR)
    try:
        query_firmware(fd, debug=debug)
        data = query_temperatures(fd, debug=debug)
        if debug:
            for i in range(0, len(data), 8):
                chunk = data[i:i+8]
                print(f'  chunk {i//8}: {chunk.hex()}  {list(chunk)}', file=sys.stderr)
            for off in range(0, min(len(data)-1, 14), 2):
                try:
                    v = struct.unpack_from('>h', data, off)[0] / 100.0
                    print(f'  offset {off:2d}: {v:+.2f} °C', file=sys.stderr)
                except struct.error:
                    pass
        return parse_internal_temp(data), parse_probe_temp(data)
    finally:
        os.close(fd)


def print_row(ts, internal_c, probe_c):
    print(f'{ts:<20}  {internal_c:>+11.2f}  {c_to_f(internal_c):>+11.2f}  {probe_c:>+8.2f}  {c_to_f(probe_c):>+8.2f}')


def get_offset(flag):
    """Return float value for --flag=N or --flag N, or 0.0 if absent."""
    for i, arg in enumerate(sys.argv):
        if arg.startswith(f'{flag}='):
            return float(arg.split('=', 1)[1])
        if arg == flag and i + 1 < len(sys.argv):
            return float(sys.argv[i + 1])
    return 0.0


def main():
    debug           = '--debug'           in sys.argv
    loop            = '--loop'            in sys.argv
    internal_offset = get_offset('--internal-offset')
    probe_offset    = get_offset('--probe-offset')

    devices = find_temper2_hidraw()
    if not devices:
        print('ERROR: No TEMPer2 device found in /sys/class/hidraw/', file=sys.stderr)
        sys.exit(1)

    path = devices[-1]
    if debug:
        print(f'All TEMPer2 hidraw devices: {devices}', file=sys.stderr)
        print(f'Using: {path}', file=sys.stderr)

    try:
        os.close(os.open(path, os.O_RDWR | os.O_NONBLOCK))
    except PermissionError:
        print(f'ERROR: Permission denied on {path}', file=sys.stderr)
        print('       Run as root, or install udev rule (see 99-temper2.rules)', file=sys.stderr)
        sys.exit(1)

    print(HDR)
    print(SEP)

    reading_count = 0
    try:
        while True:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            internal_c, probe_c = take_reading(path, debug)
            print_row(ts, internal_c + internal_offset, probe_c + probe_offset)
            reading_count += 1
            if not loop:
                break
            # reprint header every 20 rows so it stays visible while scrolling
            if reading_count % 20 == 0:
                print(SEP)
                print(HDR)
                print(SEP)
            time.sleep(30)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()

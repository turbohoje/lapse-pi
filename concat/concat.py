#!/usr/bin/env python3

import os
import subprocess

base_dir = "/Users/jmeyer/Downloads/reolink/"

def escape_spaces(input_string):
    return input_string.replace(" ", "\\ ")

def create_manifest_and_concat(prefix, output_file):
    global base_dir
    """
    Creates a manifest file from MP4 files with a given prefix, sorts them, 
    and concatenates them using FFmpeg.

    Args:
        prefix (str): The file prefix to search for.
        output_file (str): The name of the concatenated output file.
    """
    # Get list of MP4 files matching the prefix
    files = sorted([f for f in os.listdir(base_dir) if f.startswith(prefix) and f.endswith('.mp4')])
    
    if not files:
        print("No files found with the given prefix.")
        return

    # Create the manifest file
    manifest_filename = "file_list.txt"
    with open(manifest_filename, "w") as manifest:
        for file in files:
            f = escape_spaces(file)
            manifest.write(f"file '{base_dir}{file}'\n")
    
    print(f"Manifest file '{manifest_filename}' created with the following files:")
    for file in files:
        f = escape_spaces(file)
        print(f"  {base_dir}{f}")

    # Construct and run the FFmpeg command
    ffmpeg_command = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", manifest_filename, "-c", "copy", output_file
    ]

    try:
        subprocess.run(ffmpeg_command, check=True)
        print(f"Concatenation complete. Output file: {output_file}")
    except subprocess.CalledProcessError as e:
        print("Error occurred while running FFmpeg:", e)
    finally:
        # Optionally remove the manifest file
        os.remove(manifest_filename)
        print(f"Manifest file '{manifest_filename}' removed.")

# Usage example:
# Provide a prefix for the MP4 files and the desired output file name
if __name__ == "__main__":
    prefix = "House Cam-20241009"
    create_manifest_and_concat(prefix, prefix+".mp4")

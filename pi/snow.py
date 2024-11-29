#!/usr/bin/env python3

import cv2
import numpy as np
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Mark a snow stake on an image.")
parser.add_argument("filename", help="Path to the image file to be processed.")
args = parser.parse_args()

# Load the image
input_image_path = args.filename
image = cv2.imread(input_image_path)

if image is None:
    raise FileNotFoundError(f"Image file not found: {input_image_path}")

# Coordinates of the snow stake (modify based on your image's stake position)
y_offset = 8
stake_x = 2250  # Approximate x-coordinate of the snow stake
stake_top_y = 734-y_offset  # Approximate top y-coordinate of the stake
stake_bottom_y = 1347-y_offset  # Approximate bottom y-coordinate of the stake

# Stake properties
stake_height_feet = 8  # The stake is 8 feet tall
bottom_spacing = 94  # Pixels per foot at the top
top_spacing = 66  # Pixels per foot at the bottom

# Create a copy of the image to draw markers
marked_image = image.copy()

# Calculate the total stake pixel height
stake_pixel_height = stake_bottom_y - stake_top_y

# Function to interpolate spacing based on y-coordinate
def interpolate_spacing(y):
    # Linear interpolation of pixel spacing from bottom to top
    relative_position = (y - stake_top_y) / stake_pixel_height
    return bottom_spacing + relative_position * (top_spacing - bottom_spacing)

# Draw the stake markers
current_y = stake_bottom_y  # Start at the bottom
for foot in range(stake_height_feet):
    # Draw the horizontal marker line
    cv2.line(marked_image, (stake_x - 20, int(current_y)), (stake_x + 20, int(current_y)), (0, 255, 0), 2)
    
    # Add the foot label
    text_position = (stake_x + 30, int(current_y) + 5)
    label = f"{foot} ft"
    cv2.putText(marked_image, label, text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Update y-coordinate for the next marker
    current_spacing = interpolate_spacing(current_y)
    current_y -= current_spacing  # Move upward

# Draw the central vertical stake line
cv2.line(marked_image, (stake_x, stake_top_y), (stake_x, stake_bottom_y), (255, 0, 0), 2)

# Overwrite the original image
cv2.imwrite(input_image_path, marked_image)
print(f"Marked image saved to {input_image_path}")


#!/usr/bin/env python3

import cv2
import numpy as np
import os

# Get the current script directory
script_dir = os.path.dirname(os.path.abspath(__file__))


# Load the image
input_image_path = script_dir+'/snow-stake.jpg'
output_image_path = script_dir+'/snow-stake-marked.jpg'
image = cv2.imread(input_image_path)

# Coordinates of the snow stake (modify based on your image's stake position)
stake_x = 2250  # Approximate x-coordinate of the snow stake
stake_top_y = 734  # Approximate top y-coordinate of the stake
stake_bottom_y = 1347  # Approximate bottom y-coordinate of the stake

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

# Save the marked image
cv2.imwrite(output_image_path, marked_image)
print(f"Marked image saved to {output_image_path}")
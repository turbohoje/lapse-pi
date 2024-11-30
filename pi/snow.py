#!/usr/bin/env python3

import cv2
import numpy as np
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Mark snow stakes or power poles on an image.")
parser.add_argument("--image1", help="Path to the snow stake image file to be processed.")
parser.add_argument("--image2", help="Path to the power pole image file to be processed.")
args = parser.parse_args()

# Function to process a snow stake image
def process_snow_stake(image_path, stake_x, stake_top_y, stake_bottom_y, stake_height_feet, bottom_spacing, top_spacing):
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image file not found: {image_path}")

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
    cv2.imwrite(image_path, marked_image)
    print(f"Marked snow stake image saved to {image_path}")

# Function to process the power pole image with tilt
def process_power_pole(image_path, pole_bottom_x, pole_bottom_y, pole_top_x, pole_top_y, stake_height_feet, spacing):
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Create a copy of the image to draw markers
    marked_image = image.copy()

    # Calculate the pole angle
    dx = pole_top_x - pole_bottom_x
    dy = pole_top_y - pole_bottom_y
    angle = np.arctan2(dy, dx)

    # Calculate the direction vector
    unit_vector = np.array([dx, dy]) / np.sqrt(dx**2 + dy**2)

    # Draw the stake markers
    current_position = np.array([pole_bottom_x, pole_bottom_y], dtype=np.float64)
    for foot in range(stake_height_feet):
        # Calculate the marker endpoints (tilted)
        start = current_position - [20 * np.cos(angle + np.pi / 2), 20 * np.sin(angle + np.pi / 2)]
        end = current_position + [20 * np.cos(angle + np.pi / 2), 20 * np.sin(angle + np.pi / 2)]

        # Convert positions to integers for drawing
        start = start.astype(int)
        end = end.astype(int)
        text_position = (current_position + [23, 0]).astype(int)

        # Draw the tilted marker line
        cv2.line(marked_image, tuple(start), tuple(end), (0, 255, 0), 2)

        # Add the foot label (horizontal text)
        label = f"{foot} ft"
        cv2.putText(marked_image, label, tuple(text_position), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Move to the next position
        current_position += unit_vector * spacing

    # Draw the central tilted pole line
    cv2.line(marked_image, (pole_bottom_x, pole_bottom_y), (pole_top_x, pole_top_y), (255, 0, 0), 2)

    # Overwrite the original image
    cv2.imwrite(image_path, marked_image)
    print(f"Marked power pole image saved to {image_path}")

# Determine which image to process
if args.image1:
    process_snow_stake(
        args.image1,
        stake_x=2250,
        stake_top_y=722,  # Adjusted for yoffset
        stake_bottom_y=1335,  # Adjusted for yoffset
        stake_height_feet=8,
        bottom_spacing=94,
        top_spacing=66
    )
elif args.image2:
    process_power_pole(
        args.image2,
        pole_bottom_x=385,
        pole_bottom_y=835,
        pole_top_x=352,
        pole_top_y=702,
        stake_height_feet=6,
        spacing=22
    )
else:
    print("Error: You must provide either --image1 or --image2.")


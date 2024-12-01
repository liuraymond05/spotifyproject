# utils.py
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os
from collections import Counter
from datetime import datetime
from django.conf import settings


def get_spotify_access_token(user_profile):
    """Retrieve the access token for the given user profile."""
    return user_profile.spotify_access_token


def generate_wrap_summary_image(user_data):
    """Generate an image from the wrap summary text."""
    # Image size and background color
    width, height = 800, 400
    img = Image.new('RGB', (width, height), color='white')

    # Initialize drawing context
    draw = ImageDraw.Draw(img)

    # Load a font (or use default if not available)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()

    # Draw the user data on the image
    text = f"Top Artists: {', '.join(user_data['artist_names'])}\n"
    text += f"Top Albums: {', '.join(user_data['album_names'])}\n"
    text += f"Top Genre: {user_data['top_genre'] if user_data['top_genre'] else 'N/A'}"

    text_position = (50, 50)
    draw.text(text_position, text, font=font, fill="black")

    # Save the image to a BytesIO object
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return img_io


def save_wrap_summary_image(image_io):
    """Save the generated image to the server."""
    # Define the path where the image will be saved
    file_name = f"wrap_summary_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    image_path = os.path.join(settings.MEDIA_ROOT, 'wrap_summaries', file_name)

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    # Save the image
    with open(image_path, 'wb') as img_file:
        img_file.write(image_io.getvalue())

    return image_path

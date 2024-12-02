# utils.py
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import io
from collections import Counter
from datetime import datetime
from django.conf import settings


def get_spotify_access_token(user_profile):
    """Retrieve the access token for the given user profile."""
    return user_profile.spotify_access_token


def generate_wrap_summary_image(user_data):
    """Generate a visually styled Spotify Wrapped summary image."""

    # Define canvas size and colors
    image_width, image_height = 1080, 1080
    gradient_start = (30, 30, 50)  # Dark purple
    gradient_end = (100, 50, 200)  # Vibrant purple
    accent_color = (255, 215, 0)  # Gold

    # Create a blank image and a drawing object
    image = Image.new('RGB', (image_width, image_height))
    draw = ImageDraw.Draw(image)

    # Create a gradient background
    for y in range(image_height):
        r = gradient_start[0] + (gradient_end[0] - gradient_start[0]) * y // image_height
        g = gradient_start[1] + (gradient_end[1] - gradient_start[1]) * y // image_height
        b = gradient_start[2] + (gradient_end[2] - gradient_start[2]) * y // image_height
        draw.line([(0, y), (image_width, y)], fill=(r, g, b))

    # Load fonts (adjust font paths as needed)
    font_path_large = os.path.join(settings.BASE_DIR, 'spotifywrapper/static/af.ttf')
    font_path_small = os.path.join(settings.BASE_DIR, 'spotifywrapper/static/af.ttf')
    font_large = ImageFont.truetype(font_path_large, 60)
    font_small = ImageFont.truetype(font_path_small, 40)

    # Add title text
    title_text = f"My Spotify Wrapped!"
    draw.text((50, 50), title_text, font=font_large, fill=accent_color)

    # Add user data sections
    sections = [
        ("Top Genre", user_data["top_genre"]),
        ("Listening Element", user_data["listening_element"]),
        ("Favorite Decade", user_data.get("favorite_decade", "N/A")),
        ("Popularity Level", user_data.get("popularity_level", "N/A")),
        ("Top Album", user_data["top_artists"]),
    ]

    y_offset = 150
    for title, value in sections:
        draw.text((50, y_offset), f"{title}: {value}", font=font_small, fill=(255, 255, 255))
        y_offset += 100

    # Add album cover for the top album
    top_album_cover_url = user_data.get("top_album_cover", None)
    if top_album_cover_url:
        try:
            response = requests.get(top_album_cover_url)
            top_album_cover = Image.open(io.BytesIO(response.content))
            top_album_cover = top_album_cover.resize((200, 200), Image.ANTIALIAS)
            image.paste(top_album_cover, (50, y_offset))
        except Exception as e:
            print(f"Error fetching album cover: {e}")

        draw.text((300, y_offset + 75), f"Top Album: {user_data['top_album']}", font=font_small, fill=(255, 255, 255))
        y_offset += 250  # Adjust for the album image height

    # Add images of top 3 artists
    artist_images = user_data.get("artist_images", [])  # Ensure API provides images for artists
    artist_image_size = 150
    artist_image_positions = [(50, y_offset), (250, y_offset), (450, y_offset)]

    for i, image_url in enumerate(artist_images[:3]):
        try:
            # Fetch and process artist image
            response = requests.get(image_url)
            artist_image = Image.open(io.BytesIO(response.content))
            artist_image = artist_image.resize((artist_image_size, artist_image_size), Image.ANTIALIAS)
            image.paste(artist_image, artist_image_positions[i])
        except Exception as e:
            print(f"Error fetching artist image: {e}")

    # Save the image to an in-memory file
    image_io = io.BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)

    return image_io


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

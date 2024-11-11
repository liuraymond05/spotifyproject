import requests
from django.conf import settings
from django.utils import timezone
import datetime

def refresh_access_token(user_profile):
    """Refreshes and updates the Spotify access token."""
    refresh_token = user_profile.spotify_refresh_token
    token_response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.SPOTIPY_CLIENT_ID,
            "client_secret": settings.SPOTIPY_CLIENT_SECRET,
        },
    )
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")

    if access_token:
        user_profile.spotify_access_token = access_token
        user_profile.token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
        user_profile.save()
        return access_token

    return None

def get_spotify_api_client(user):
    """Generates a client with Spotify API access for the given user."""
    user_profile = user.userprofile
    access_token = user_profile.spotify_access_token

    # Refresh token if expired
    if user_profile.token_expires <= timezone.now():
        access_token = refresh_access_token(user_profile)

    if not access_token:
        return None

    class SpotifyClient:
        def __init__(self, access_token):
            self.access_token = access_token

        def get_top_tracks(self):
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get("https://api.spotify.com/v1/me/top/tracks?limit=10", headers=headers)
            return response.json().get('items', [])

    return SpotifyClient(access_token)

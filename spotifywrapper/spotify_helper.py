import requests
from django.conf import settings
from django.utils import timezone
import datetime
import random

def refresh_access_token(user_profile):
    """
    Refreshes and updates the Spotify access token for the given user profile.

    This function sends a POST request to the Spotify API to refresh the access token 
    using the user's refresh token. If the refresh is successful, the new access token 
    and its expiration time are saved in the user's profile.

    Args:
        user_profile (UserProfile): The UserProfile instance associated with the user 
                                     whose access token needs to be refreshed.

    Returns:
        str or None: The new access token if the refresh is successful, or None if 
                     the refresh failed (e.g., if no access token was returned).
    """
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
    """
    Generates a client with Spotify API access for the given user.

    This function checks if the user's access token has expired and, if necessary, 
    refreshes it using the `refresh_access_token` function. It then generates a 
    `SpotifyClient` instance that can interact with the Spotify API to fetch data like 
    top tracks.

    Args:
        user (User): The user object associated with the Spotify profile for which 
                     the client will be created.

    Returns:
        SpotifyClient or None: An instance of `SpotifyClient` if the access token is valid, 
                                or None if there was an issue (e.g., token expiration or failure 
                                to refresh the token).
    """
    user_profile = user.userprofile
    access_token = user_profile.spotify_access_token

    # Refresh token if expired
    if user_profile.token_expires <= timezone.now():
        access_token = refresh_access_token(user_profile)

    if not access_token:
        return None

    class SpotifyClient:
        def __init__(self, access_token):
            """
            Initializes the SpotifyClient with the provided access token.

            Args:
                access_token (str): The access token used to authenticate API requests.
            """
            self.access_token = access_token

        def get_top_tracks(self):
            """
            Fetches the user's top tracks from Spotify.

            Sends a request to the Spotify API to retrieve the top tracks of the user 
            based on the provided access token.

            Returns:
                list: A list of dictionaries containing details of the top tracks 
                      (track name, artist, album, etc.).
            """
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get("https://api.spotify.com/v1/me/top/tracks?limit=10", headers=headers)
            return response.json().get('items', [])

    return SpotifyClient(access_token)

def get_user_top_tracks(access_token, limit=10):
    """
    Fetches the user's top tracks from Spotify.

    This function sends a request to the Spotify API to retrieve the top tracks of 
    the user for the specified time range. The result is a list of top tracks with 
    relevant details such as track name, artist, album, and preview URL.

    Args:
        access_token (str): The access token used to authenticate the request.
        limit (int): The number of top tracks to retrieve. Default is 10.

    Returns:
        list: A list of dictionaries containing details for the top tracks (name, artist, 
              album, ID, and preview URL).
        If there is an error or the request fails, an empty list is returned.
    """
    url = "https://api.spotify.com/v1/me/top/tracks"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "limit": limit,
        "time_range": "medium_term"  # Options: short_term, medium_term, long_term
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        tracks = response.json().get('items', [])
        return [
            {
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "album": track["album"]["name"],
                "id": track["id"],
                "preview_url": track.get("preview_url"),
            }
            for track in tracks
        ]
    else:
        print(f"Error fetching top tracks: {response.status_code} - {response.json()}")
        return []

def select_random_tracks(tracks, count=3):
    """
    Selects a random subset of tracks from a given list.

    This function takes a list of tracks and selects a random subset from it. If there 
    are not enough tracks to choose from, it will return all available tracks.

    Args:
        tracks (list): The list of tracks to select from.
        count (int): The number of tracks to select. Default is 3.

    Returns:
        list: A list of randomly selected tracks. If there are fewer tracks than the 
              specified count, all tracks will be returned.
    """
    if len(tracks) < count:
        print("Not enough tracks to select from.")
        return tracks
    return random.sample(tracks, count)
from collections import Counter
from django.conf import settings
import os
import random
import json
from urllib.parse import quote_plus
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import base64
from django.utils.translation import get_language, activate, get_language_from_request
from spotifyproject.settings import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from .forms import PasswordResetCustomForm, CustomUserForm
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.shortcuts import render, redirect
from django.conf import settings
import os
import requests
from .models import UserProfile
from .utils import get_spotify_access_token, generate_wrap_summary_image, save_wrap_summary_image
from collections import Counter

def login_view(request):
    """Handles user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            user_profile = UserProfile.objects.filter(user=user).first()

            if user_profile is None:
                user_profile = UserProfile(user=user)
                user_profile.save()

            if not user_profile.spotify_access_token:
                return redirect('spotify_login')

            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Logs out the user and redirects to the login page."""
    logout(request)
    return redirect('login')

@login_required
@login_required
def home(request):
    """Renders the home page with Spotify profile information."""
    user_profile = UserProfile.objects.filter(user=request.user).first()

    if not user_profile or not user_profile.spotify_access_token:
        # Redirect to Spotify login if the user hasn't authenticated with Spotify
        return redirect('spotify_login')

    try:
        access_token = get_spotify_access_token(user_profile)
        profile_response = requests.get(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        profile_data = profile_response.json()

        top_tracks_response = requests.get(
            'https://api.spotify.com/v1/me/top/tracks?limit=10',  # Limit to top 10 tracks
            headers={'Authorization': f'Bearer {access_token}'}
        )
        top_tracks_data = top_tracks_response.json()
        top_tracks = []
        for track in top_tracks_data['items']:
            top_tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'preview_url': track['preview_url']
            })

        if profile_response.status_code == 200:
            username = profile_data.get('display_name', 'Unknown')  # Get the Spotify username
            return render(request, 'home.html', {
                'profile': profile_data,
                'top_tracks': top_tracks,
                'username': username  # Pass the Spotify username to the template
            })
        else:
            messages.error(request, "Failed to fetch Spotify profile information.")
            return redirect('spotify_login')

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('login')



# Spotify API credentials and URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


def spotify_login(request):

    """Initiates Spotify login and authorization flow"""
    if not request.user.is_authenticated:
        return redirect('login')

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = None

    # If user doesn't have a valid Spotify token, start the authentication flow
    if user_profile is None or not user_profile.spotify_access_token:
        redirect_uri = SPOTIFY_REDIRECT_URI
        scope = "user-top-read user-read-recently-played user-library-read"
        auth_url = (
            f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={SPOTIFY_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}&scope={scope}"

        )
        return redirect(auth_url)
    return redirect('home')

def gamepage(request):
    """
    Game view that fetches the user's top tracks and selects three random tracks for the game.
    """
    # Retrieve the access token from the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        messages.error(request, "No Spotify access token found. Please log in to play the game.")
        return redirect('login')  # Redirect to login page

    access_token = user_profile.spotify_access_token

    # Check if the token has expired
    if user_profile.token_expires and timezone.now() >= user_profile.token_expires:
        messages.error(request, "Your Spotify session has expired. Please log in again.")
        return redirect('login')  # Redirect to login page

    # Call Spotify API to get user's top tracks
    headers = {"Authorization": f"Bearer {access_token}"}
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=50"
    response = requests.get(top_tracks_url, headers=headers)

    # Handle API response
    if response.status_code == 401:  # 401 Unauthorized - token invalid
        messages.error(request, "Your session has expired or is invalid. Please log in again.")
        return redirect('login')  # Redirect to login page
    elif response.status_code != 200:  # Other API errors
        messages.error(request, "Failed to load tracks from Spotify. Please try again later.")
        return redirect('home')  # Redirect to home page

    # Parse and format the tracks data
    tracks_data = response.json().get("items", [])
    tracks = [
        {
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else "/static/spotifywrapped/placeholderimage.jpg",
            "id": track["id"],
            "album_id": track["album"]["id"],  # Include album ID for grouping
        }
        for track in tracks_data
    ]

    if not tracks:
        messages.error(request, "No top tracks found on Spotify. Please listen to more music and try again!")
        return redirect('home')

    # Prepare game data
    game_data = []
    for track in tracks:
        correct_song = track["title"]
        album_cover = track["album_cover"]

        # Generate distractors (other tracks not from the same album)
        other_tracks = [t["title"] for t in tracks if t["album_id"] != track["album_id"]]
        distractors = random.sample(other_tracks, 2) if len(other_tracks) >= 2 else []

        # Add round data
        game_data.append({
            "album_cover": album_cover,
            "correct_song": correct_song,
            "options": random.sample([correct_song] + distractors, len(distractors) + 1),
        })

    # Pass tracks and game data to the template
    return render(request, "spotifywrapper/games.html", {"game_data": game_data, "tracks": tracks})

@login_required
def spotify_callback(request):
    """Handles Spotify's callback with the authorization code"""
    code = request.GET.get('code')
    if code:
        # Exchange the authorization code for an access token
        redirect_uri = SPOTIFY_REDIRECT_URI

        auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        b64 = base64.b64encode(auth_str.encode()).decode()

        token_request_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }

        token_response = requests.post(
            SPOTIFY_TOKEN_URL,
            data=token_request_data,
            headers={
                "Authorization": f"Basic {b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
        )


        token_data = token_response.json()
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in')

        if access_token and refresh_token:
            user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            user_profile.spotify_access_token = access_token
            user_profile.spotify_refresh_token = refresh_token
            user_profile.token_expires = timezone.now() + timedelta(seconds=expires_in)
            user_profile.save()
            return redirect('home')

    messages.error(request, "Spotify authentication failed. No code provided.")
    return redirect('login')

def refresh_spotify_token(user_profile):
    """Refreshes the Spotify access token if expired."""
    refresh_token = user_profile.spotify_refresh_token
    if refresh_token:
        token_response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            },
        )
        token_data = token_response.json()

        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in')

        if access_token:
            user_profile.spotify_access_token = access_token
            user_profile.token_expires = timezone.now() + timedelta(seconds=expires_in)
            user_profile.save()
            return access_token

    return None  # If refresh failed or there was no refresh token


def get_spotify_access_token(user_profile):
    """Get the Spotify access token, refreshing it if necessary."""
    if timezone.now() > user_profile.token_expires:
        # Token has expired, refresh it
        new_access_token = refresh_spotify_token(user_profile)
        if not new_access_token:
            raise Exception("Unable to refresh Spotify access token.")
        return new_access_token
    else:
        # Return the existing token
        return user_profile.spotify_access_token



@login_required
def get_spotify_profile(request):
    "Fetches the access token from the Spotify API and the User's Profile."

    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        messages.error(request, "Spotify authentication failed.")
        return redirect('spotify_login')
    try:
        access_token = get_spotify_access_token(user_profile)
        profile_response = requests.get(
            'https://api.spotify.com/v1/me',
            headers={
                "Authorization": f"Bearer {access_token}"
            },
        )
        profile_data = profile_response.json()
        if profile_response.status_code == 200:
            return render(request, 'home.html', {'profile': profile_data})
        else:
            error_message = profile_data.get('error', {}).get('message', 'Failed to fetch Spotify profile')
            messages.error(request, error_message)
            return redirect('home')
    except Exception as e:
        messages.error(request, "Spotify authentication failed.")
        return redirect('home')




def register_view(request):
    """Handles the user's ability to make an account."""
    form = CustomUserForm()

    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You have successfully created an account!')
            return redirect('login')
    else:
        messages.error(request, 'Please complete the entire form.')
    return render(request, 'spotifywrapper/register.html', {'form': form})



def reset_password_view(request):
    """Handles the user's ability to reset their password."""
    if request.method == 'POST':
        form = PasswordResetCustomForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password_new = form.cleaned_data['new_password1']

            try:
                user = User.objects.get(username=username)
                user.set_password(password_new)
                user.save()
                messages.success(request, 'Your password was successfully updated!')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'This user does not exist.')
    else:
        form = PasswordResetCustomForm()
    return render(request, 'spotifywrapper/reset.html', {"form": form})
def user_settings(request):
    language_code = request.LANGUAGE_CODE  # Use get_language to get the current language
    return render(request, 'settings.html', {
        'language_code': language_code,
    })

@login_required
def delete_account(request):
    """Handles the deletion of an account."""
    if request.method == 'POST':
        user = request.user
        user.delete()  # This will delete the user from the database

        # Log out the user immediately after deletion
        logout(request)

        # Add a success message and redirect to home or login page
        messages.success(request, "Your account has been deleted successfully.")
        return redirect('login')  # Or redirect to login page if preferred

    return render(request, 'settings/delete_account.html')
def contact_developers(request):
    # Render a template that displays the contact information or a contact form
    return render(request, 'contact_developers.html')


def set_language(request):
    """Handles changing the language in settings."""

    if request.method == 'POST':
        #Get the current language
        language_code = request.POST.get('language')

        # Define supported languages
        supported_languages = ['en', 'es', 'fr']

        # If the language code is not supported, redirect back to the referring page or fallback to home
        if language_code not in supported_languages:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))  # Redirect to previous page or home if unsupported

        # Activate the selected language
        activate(language_code)

        # Store the selected language in the session
        if hasattr(request, 'session'):
            request.session['django_language'] = language_code

        # Create the redirect response and set the language cookie
        response = HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        response.set_cookie('django_language', language_code)  # Store the selected language in the cookie

        return response
    # In case the form method isn't POST, redirect back
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def top_spotify_data(request):
    """
    View to get the user's top tracks, artists, genre, decade, top song popularity, and element.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Fetch the Spotify profile to get the username
    profile_response = requests.get(
        'https://api.spotify.com/v1/me',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    username = profile_response.json().get('display_name', 'Unknown') if profile_response.status_code == 200 else 'Unknown'


    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = request.GET.get('time_range', 'long_term')

    top_tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=5',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_tracks = []
    if top_tracks_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']

    top_tracks_data = []
    for track in top_tracks:
        top_tracks_data.append({
            'name': track['name'],
            'artist': ', '.join([artist['name'] for artist in track['artists']]),
            'album': track['album']['name'],
            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'preview_url': track['preview_url'],
            'popularity': track['popularity'],

        })


    # Fetch the top artists (limit to 10) based on the selected time range
    top_artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_artists_data = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            top_artists_data.append({
                'name': artist['name'],
                'image': artist['images'][0]['url'] if 'images' in artist else None,
            })
    else:
        return redirect('home')  # Redirect back if there was an error fetching top artists
    


    # Get the top genre (most frequent genre from top artists)
    genres = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            genres.extend(artist.get('genres', []))  # Add all genres associated with each artist

    # Determine the top genre (most frequent genre in the list)
    top_genre = max(Counter(genres), key=Counter(genres).get) if genres else None

    # Get the top album
    album_count = {}
    album_details = {}
    for track in top_tracks:
        album_name = track['album']['name']
        album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
        album_release_date = track['album']['release_date']

        album_count[album_name] = album_count.get(album_name, 0) + 1
        if album_name not in album_details:
            album_details[album_name] = {
                'name': album_name,
                'image': album_image,
                'release_date': album_release_date,
                'details': track['album'].get('label', 'Unknown')  # You can use this for additional album details
            }
    top_album = max(album_count, key=album_count.get) if album_count else None
    album_details = album_details.get(top_album, None)

    decades = [int(track['album']['release_date'][:4]) // 10 * 10 for track in top_tracks if
               'release_date' in track['album']]
    favorite_decade = max(set(decades), key=decades.count) if decades else None
    favorite_decade = f"{favorite_decade}" if favorite_decade else None

    top_song = None
    top_popularity = None
    popularity_level = None
    if top_tracks:
        top_song = top_tracks[0]['name']
        top_popularity = top_tracks[0]['popularity']

        # Define popularity thresholds
        if top_popularity >= 80:
            popularity_level = 'High'
        elif top_popularity >= 50:
            popularity_level = 'Medium'
        else:
            popularity_level = 'Low'

    # Define the genre-to-element mapping
    genre_to_element = {
        'country': 'earth','folk': 'earth','bluegrass': 'earth','americana': 'earth','indie folk': 'earth',
        'acoustic': 'earth','blues': 'earth','soul': 'earth','reggae': 'earth',
        'alternative rock': 'earth','indie': 'earth',

        'hard rock': 'fire','metal': 'fire','punk rock': 'fire','trap': 'fire','salsa': 'fire',
        'hip-hop': 'fire', 'punk': 'fire','emo': 'fire','edm': 'fire','dancehall': 'fire',
        'pop': 'fire','rap': 'fire',

        'r&b': 'water','lo-fi hip-hop': 'water','chillout': 'water','chillwave': 'water',
        'smooth jazz': 'water','bossa nova': 'water','reggaeton': 'water','tango': 'water',
        'lofi': 'water','jazz': 'water',

        'indie pop': 'air','synthpop': 'air','electropop': 'air','k-pop': 'air','alternative indie': 'air',
        'funk': 'air','disco': 'air','afrobeats': 'air','experimental': 'air','ambient': 'air','classical': 'air',
        'jazz fusion': 'air','progressive rock': 'air','synthwave': 'air'
    }

    # Default to 'Unknown' if the genre doesn't match any known category
    user_element = genre_to_element.get(top_genre, 'air')


    return render(request, 'spotifywrapper/wrapped.html', {
        'top_genre': top_genre,
        'top_artists': top_artists_data,
        'selected_time_range': time_range,  # Pass the selected time range to the template
        'top_song': top_song,
        'user_element': user_element,
        'username': username, # Pass the username to the template
        'favorite_decade': favorite_decade,
        'popularity_level': popularity_level,
        'top_album': top_album,
        'top_tracks': top_tracks_data,
        'album_details': album_details,

    })

def gamepage(request):
    """Renders the gamepage."""
    return render(request, 'games.html')
def wraps(request):
    """Renders the savedwraps page."""
    return render(request, 'savedwraps.html')
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SavedWrap  # Assuming you have a SavedWrap model to store wrapped data


from django.http import JsonResponse
from .models import SavedWrap

@csrf_exempt
def save_wrap(request):
    """
    View that saves the user's Spotify data into the SavedWrap model.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify
    access_token = get_spotify_access_token(user_profile)
    time_range = request.POST.get('time_range', 'long_term')

    # Fetch top tracks and artists
    top_tracks_data = get_top_tracks(access_token, time_range)
    top_artists_data = get_top_artists(access_token, time_range)
    print(top_artists_data)

    # Now that top_artists_data is available, you can safely call get_top_genre
    top_genre_data = get_top_genre(access_token, time_range)
    top_album_data = get_top_album(top_tracks_data)
    top_song_data = get_top_song(top_tracks_data)
    user_element_data = get_user_element(top_genre_data)
    favorite_decade_data = get_favorite_decade(top_tracks_data)
    popularity_data = get_popularity_level(top_tracks_data)

    # Save the data to the SavedWrap model
    saved_wrap = SavedWrap(
        username=request.user.username,
        time_range=time_range,
        top_genre=top_genre_data,
        top_album=top_album_data,
        top_artists=top_artists_data,
        top_tracks=top_tracks_data,
        top_song=top_song_data,
        user_element=user_element_data,
        favorite_decade=favorite_decade_data,
        top_song_popularity=popularity_data  # Should be 'High', 'Medium', or 'Low'
    )
    saved_wrap.save()
    print(saved_wrap)

    return redirect('savedwraps')


def get_top_song(top_tracks):
    """Fetches the top song."""
    return top_tracks[0]['name']

def get_top_tracks(access_token, time_range='long_term', limit=3):
    """Fetches the user's top tracks."""
    response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit={limit}',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    if response.status_code == 200:
        return response.json()['items']
    return []

def get_top_artists(access_token, time_range='long_term', limit=3):
    """
    Fetch the top 3 artists from Spotify based on the provided time range.

    :param access_token: Spotify API access token
    :param time_range: The time range ('long_term', 'medium_term', 'short_term')
    :param limit: Number of top artists to fetch (default is 3)
    :return: A list of dictionaries containing artist names and images
    """
    try:
        # Fetch top artists from Spotify API
        top_artists_response = requests.get(
            f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit={limit}',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        # Handle API response
        if top_artists_response.status_code == 200:
            # Parse the response and extract relevant data
            top_artists = top_artists_response.json().get('items', [])
            top_artists_data = [
                {
                    'name': artist['name'],
                    'image': artist['images'][0]['url'] if artist.get('images') else None
                }
                for artist in top_artists
            ]
            return top_artists_data
        else:
            # Log the error and return an empty list on failure
            print(f"Error fetching top artists: {top_artists_response.status_code}")
            return [{'name': 'Unknown Artist', 'image': None} for _ in range(3)]

    except Exception as e:
        # Handle unexpected errors
        print(f"An error occurred: {e}")
        return [{'name': 'Unknown Artist', 'image': None} for _ in range(3)]


def get_top_genre(access_token, time_range='long_term'):
    """
    Function to retrieve the top genre from the user's top artists on Spotify.

    Parameters:
    - access_token (str): The Spotify access token for the user.
    - time_range (str): The time range to get top artists data ('long_term', 'medium_term', or 'short_term').

    Returns:
    - str: The most frequent genre from the user's top artists.
    """
    # Fetch the user's top artists
    top_artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    genres = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            genres.extend(artist.get('genres', []))  # Add all genres associated with each artist

    # Determine the top genre (most frequent genre in the list)
    top_genre = max(Counter(genres), key=Counter(genres).get) if genres else None

    return top_genre


def get_top_album(top_tracks):
    """Fetches the user's top album, as well as album information."""
    album_count = {}
    album_details = {}
    for track in top_tracks:
        album_name = track['album']['name']
        album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
        album_release_date = track['album']['release_date']

        album_count[album_name] = album_count.get(album_name, 0) + 1
        if album_name not in album_details:
            album_details[album_name] = {
                'name': album_name,
                'image': album_image,
                'release_date': album_release_date,
                'details': track['album'].get('label', 'Unknown')
            }
    top_album = max(album_count, key=album_count.get) if album_count else None
    return album_details.get(top_album, None)

def get_favorite_decade(top_tracks):
    """Determines a user's favorite decade for listening."""
    decades = [int(track['album']['release_date'][:4]) // 10 * 10 for track in top_tracks if 'release_date' in track['album']]
    favorite_decade = max(set(decades), key=decades.count) if decades else None
    return f"{favorite_decade}" if favorite_decade else None

def get_popularity_level(top_tracks):
    """Determines the popularity of a user's favorite song."""
    top_song = None
    top_popularity = None
    popularity_level = None

    # Check if top_tracks is not empty
    if top_tracks:
        # Assuming top_tracks is a list of dictionaries with track data
        top_song = top_tracks[0]['name']  # First track as the top song
        top_popularity = top_tracks[0]['popularity']  # Popularity of the top song

        # Define popularity thresholds
        if top_popularity >= 80:
            popularity_level = 'High'
        elif top_popularity >= 50:
            popularity_level = 'Medium'
        else:
            popularity_level = 'Low'

    return popularity_level


def get_user_element(top_genre):
    """Determines a user's classical element depending on their favorite genre."""
    genre_to_element = {
        'country': 'earth', 'folk': 'earth', 'bluegrass': 'earth', 'americana': 'earth', 'indie folk': 'earth',
        'acoustic': 'earth', 'blues': 'earth', 'soul': 'earth', 'reggae': 'earth', 'alternative rock': 'earth', 'indie': 'earth',
        'hard rock': 'fire', 'metal': 'fire', 'punk rock': 'fire', 'trap': 'fire', 'salsa': 'fire',
        'hip-hop': 'fire', 'punk': 'fire', 'emo': 'fire', 'edm': 'fire', 'dancehall': 'fire',
        'pop': 'fire', 'rap': 'fire',
        'r&b': 'water', 'lo-fi hip-hop': 'water', 'chillout': 'water', 'chillwave': 'water',
        'smooth jazz': 'water', 'bossa nova': 'water', 'reggaeton': 'water', 'tango': 'water',
        'lofi': 'water', 'jazz': 'water',
        'indie pop': 'air', 'synthpop': 'air', 'electropop': 'air', 'k-pop': 'air', 'alternative indie': 'air',
        'funk': 'air', 'disco': 'air', 'afrobeats': 'air', 'experimental': 'air', 'ambient': 'air', 'classical': 'air',
        'jazz fusion': 'air', 'progressive rock': 'air', 'synthwave': 'air'
    }
    return genre_to_element.get(top_genre, 'air')



from django.shortcuts import render
from .models import SavedWrap

def saved_wraps(request):
    """Renders the SavedWrap objects onto the savedwrap page."""
    saved_wraps = SavedWrap.objects.filter(username=request.user.username)
    print(saved_wraps)
    return render(request, 'spotifywrapper/savedwraps.html', {'wraps': saved_wraps})

def delete_wrap(request, wrap_id):
    """View to delete a saved wrap."""
    if request.method == 'POST':
        wrap = get_object_or_404(SavedWrap, id=wrap_id, username=request.user.username)
        wrap.delete()  # Delete the wrap from the database
        messages.success(request, "Your saved wrap was successfully deleted!")
        return redirect('savedwraps')  # Redirect to the saved wraps page after deletion

def top_genre(request):
    """
    View to get the user's top genre from their top artists on Spotify and display it in the template.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long_term' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the user's top artists
    top_artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    genres = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            genres.extend(artist.get('genres', []))  # Add all genres associated with each artist

    # Determine the top genre (most frequent genre in the list)
    top_genre = max(Counter(genres), key=Counter(genres).get) if genres else None

    # Additional genre data for visualization or debugging
    genre_counts = Counter(genres)

    return render(request, 'spotifywrapper/top-genre.html', {
        'top_genre': top_genre,
        'genre_counts': genre_counts,  # Pass genre counts for additional context or visualizations
        'genres': genres,  # Pass all genres if needed for the template
        'repeat_times': range(10)
    })

@login_required
def top_artists(request):
    """
    View to fetch and display the user's top artists from Spotify.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long_term' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the user's top artists
    top_artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    top_artists_data = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            top_artists_data.append({
                'name': artist['name'],
                'image': artist['images'][0]['url'] if 'images' in artist and artist['images'] else None,
                'genres': artist.get('genres', []),
                'popularity': artist.get('popularity', 'Unknown'),
            })

    return render(request, 'spotifywrapper/top-artists.html', {
        'top_artists': top_artists_data,
        'selected_time_range': time_range,  # Pass the selected time range to the template
    })


@login_required
def top_albums(request):
    """
    View to get the user's top albums and display them in the template.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long_term' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    top_tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=5',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_songs = []
    if top_tracks_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']
        for track in top_tracks:
            top_songs.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'preview_url': track['preview_url']
            })

    # Organize album data
    album_count = {}
    album_details = {}
    for track in top_tracks:
        album_name = track['album']['name']
        album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
        album_release_date = track['album']['release_date']

        album_count[album_name] = album_count.get(album_name, 0) + 1
        if album_name not in album_details:
            album_details[album_name] = {
                'name': album_name,
                'image': album_image,
                'release_date': album_release_date,
                'details': track['album'].get('label', 'Unknown')  # You can use this for additional album details
            }

    # Get the top album (the one most frequently appearing in top tracks)
    top_album = max(album_count, key=album_count.get) if album_count else None
    album_details = album_details.get(top_album, None)

    # Pass the top album details to the template
    return render(request, 'spotifywrapper/top-albums.html', {
        'top_album': top_album,
        'album_details': album_details,
        'top_tracks': top_tracks,  # You can also pass the list of top tracks to show more albums
    })


@login_required
def top_songs(request):
    """
    View to display the user's top songs based on Spotify data.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if Spotify is not authenticated

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long_term' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the user's top tracks
    tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=10',  # Fetch the top 10 tracks
        headers={'Authorization': f'Bearer {access_token}'}
    )

    top_tracks = []
    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json().get('items', [])
        for track in tracks_data:
            # Extract relevant details for each track
            top_tracks.append({
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'url': track['external_urls']['spotify'],
            })

    return render(request, 'spotifywrapper/top-songs.html', {
        'top_songs': top_tracks,
        'selected_time_range': time_range,  # Pass the selected time range to the template
    })

@login_required
def user_element(request):
    """
    View to display the user's classical element based on their music taste.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long_term' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the top artists (limit to 3) based on the selected time range
    top_artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_artists_data = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            top_artists_data.append({
                'name': artist['name'],
                'image': artist['images'][0]['url'] if 'images' in artist else None,
            })
    else:
        return redirect('home')  # Redirect back if there was an error fetching top artists

    genres = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            genres.extend(artist.get('genres', []))  # Add all genres associated with each artist

    # Determine the top genre (most frequent genre in the list)
    top_genre = max(Counter(genres), key=Counter(genres).get) if genres else None

    # Define the genre-to-element mapping
    genre_to_element = {
        'country': 'earth', 'folk': 'earth', 'bluegrass': 'earth', 'americana': 'earth', 'indie folk': 'earth',
        'acoustic': 'earth', 'blues': 'earth', 'soul': 'earth', 'reggae': 'earth',
        'alternative rock': 'earth', 'indie': 'earth',

        'hard rock': 'fire', 'metal': 'fire', 'punk rock': 'fire', 'trap': 'fire', 'salsa': 'fire',
        'hip-hop': 'fire', 'punk': 'fire', 'emo': 'fire', 'edm': 'fire', 'dancehall': 'fire',
        'pop': 'fire', 'rap': 'fire',

        'r&b': 'water', 'lo-fi hip-hop': 'water', 'chillout': 'water', 'chillwave': 'water',
        'smooth jazz': 'water', 'bossa nova': 'water', 'reggaeton': 'water', 'tango': 'water',
        'lofi': 'water', 'jazz': 'water',

        'indie pop': 'air', 'synthpop': 'air', 'electropop': 'air', 'k-pop': 'air', 'alternative indie': 'air',
        'funk': 'air', 'disco': 'air', 'afrobeats': 'air', 'experimental': 'air', 'ambient': 'air', 'classical': 'air',
        'jazz fusion': 'air', 'progressive rock': 'air', 'synthwave': 'air'
    }

    # Default to 'Unknown' if the genre doesn't match any known category
    user_element = genre_to_element.get(top_genre, 'air')

    return render(request, 'spotifywrapper/top-playlist.html', {
        'top_genre': top_genre,
        'user_element': user_element,
    })


@login_required
def favorite_decade(request):
    """
    View to display the user's favorite decade based on Spotify data.
    Dynamically fetches data based on time range: short_term, medium_term, or long_term.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the user's top tracks based on the selected time range
    tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?limit=50&time_range={time_range}',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    decade_count = {}
    top_decade = None
    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json().get('items', [])
        for track in tracks_data:
            release_date = track['album']['release_date']
            if release_date:
                year = int(release_date[:4])
                decade = (year // 10) * 10  # Calculate the decade (e.g., 1980, 1990)
                decade_count[decade] = decade_count.get(decade, 0) + 1

        if decade_count:
            top_decade = max(decade_count, key=decade_count.get)

    decade_data = [{'decade': decade, 'count': count} for decade, count in decade_count.items()]
    decade_data.sort(key=lambda x: x['decade'])  # Sort decades chronologically

    return render(request, 'spotifywrapper/favorite-decade.html', {
        'decade_data': decade_data,
        'top_decade': top_decade,
    })


@login_required
def popularity_level(request):
    """
    View to determine the user's top song's popularity level on Spotify platforms.
    Dynamically fetches data based on time range: short_term, medium_term, or long_term.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    top_tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=5',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_tracks = []
    if top_tracks_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']

    top_tracks_data = []
    for track in top_tracks:
        top_tracks_data.append({
            'name': track['name'],
            'artist': ', '.join([artist['name'] for artist in track['artists']]),
            'album': track['album']['name'],
            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'preview_url': track['preview_url'],
            'popularity': track['popularity'],

        })

    top_song = None
    top_popularity = None
    popularity_level = None
    if top_tracks:
        top_song = top_tracks[0]['name']
        top_popularity = top_tracks[0]['popularity']

        # Define popularity thresholds
        if top_popularity >= 80:
            popularity_level = 'High'
        elif top_popularity >= 50:
            popularity_level = 'Medium'
        else:
            popularity_level = 'Low'

    return render(request, 'spotifywrapper/favorite-mood.html', {
        'top_song': top_song,
        'popularity_level': popularity_level,
    })


@login_required
def top_three_tracks(request):
    """
    View to display the top three tracks based on the user's Spotify data.
    Dynamically fetches data based on time range: short_term, medium_term, or long_term.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the user's top tracks (limit to 3) based on the selected time range
    tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?limit=3&time_range={time_range}',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    tracks_data = tracks_response.json().get('items', []) if tracks_response.status_code == 200 else []

    return render(request, 'spotifywrapper/top-three-tracks.html', {
        'tracks': tracks_data
    })


@login_required
def listening_habits(request):
    """
    View to display the listening habits of the user based on their Spotify data.
    This could include favorite genres, top tracks, and top artists.
    Dynamically fetches data based on time range: short_term, medium_term, or long_term.
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set in session

    # Map the session value to the appropriate Spotify time range
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')  # Ensure we have a valid time range

    # Fetch the user's top tracks (limit to 5 for variety)
    tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?limit=5&time_range={time_range}',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    # Fetch the user's top artists (limit to 5 for variety)
    artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?limit=5&time_range={time_range}',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    tracks_data = tracks_response.json().get('items', []) if tracks_response.status_code == 200 else []
    artists_data = artists_response.json().get('items', []) if artists_response.status_code == 200 else []

    return render(request, 'spotifywrapper/listening-habits.html', {
        'tracks': tracks_data,
        'artists': artists_data
    })
@login_required
def end_wrapped(request):
    """
    View to display the end-of-year summary page (Spotify Wrapped or similar).
    """
    # Retrieve the user profile
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect to login if Spotify is not authenticated

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Fetch the user's top tracks, top artists, or other data to display
    top_tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?time_range=long_term&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_artists_response = requests.get(
        'https://api.spotify.com/v1/me/top/artists?time_range=long_term&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    # Check if the requests were successful
    if top_tracks_response.status_code == 200 and top_artists_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']
        top_artists = top_artists_response.json()['items']
    else:
        top_tracks = []
        top_artists = []

    # Render the 'wrapped' page with the gathered data
    return render(request, 'spotifywrapper/end_wrapped.html', {
        'top_tracks': top_tracks,
        'top_artists': top_artists,
    })
def get_user_data(access_token, time_range='long_term'):
    """
    Fetch user data from Spotify API including top genre, top artists, album, and other elements.
    Dynamically fetches based on the specified time range using modular get_ methods.
    """
    user_data = {
        "top_genre": "N/A",
        "top_artists": [],
        "artist_images": [],
        "top_album": "N/A",
        "listening_element": "N/A",
        "favorite_decade": "N/A",
        "popularity_level": "N/A",
    }

    try:
        top_tracks_data = get_top_tracks(access_token, time_range)
        top_artists_data = get_top_artists(access_token, time_range)

        # Use the modular methods to populate user data
        user_data["top_genre"] = get_top_genre(access_token, time_range)
        user_data["top_album"] = get_top_album(top_tracks_data)
        user_data["top_artists"] = get_top_song(top_tracks_data)
        user_data["artist_images"] = [
            artist.get('images', [{}])[0].get('url', None) for artist in top_tracks_data[:3]
        ]
        user_data["listening_element"] = get_user_element(user_data["top_genre"])
        user_data["favorite_decade"] = get_favorite_decade(top_tracks_data)
        user_data["popularity_level"] = get_popularity_level(top_tracks_data)

    except Exception as e:
        # Log the error or handle it as needed
        print(f"Error fetching user data: {e}")

    return user_data

def share_wrap(request):
    """Generate the wrap summary image and provide shareable links."""
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Get the time range selected by the user from the session (default to 'long_term' if not set)
    time_range = request.session.get('term', 'long')  # 'long' is the default value if not set
    time_range_mapping = {
        'long': 'long_term',
        'medium': 'medium_term',
        'short': 'short_term',
    }
    time_range = time_range_mapping.get(time_range, 'long_term')

    # Retrieve user data
    user_data = get_user_data(access_token, time_range)

    # Generate the image
    image_io = generate_wrap_summary_image(user_data)

    # Save the image to the server
    image_path = save_wrap_summary_image(image_io)

    # Generate the image URL
    image_url = os.path.join(settings.MEDIA_URL, 'wrap_summaries', os.path.basename(image_path))

    # Generate Twitter and LinkedIn shareable URLs
    twitter_share_url = f"https://twitter.com/intent/tweet?text=Check%20out%20my%20wrap%20summary&url={image_url}"
    linkedin_share_url = f"https://www.linkedin.com/sharing/share-offsite/?url={image_url}&title=My%20Spotify%20Wrapped&summary=Check%20out%20my%20Spotify%20Wrapped%20summary!"
    instagram_share_url = 'https://www.instagram.com/'

    context = {
        'image_url': image_url,
        'twitter_share_url': twitter_share_url,
        'linkedin_share_url': linkedin_share_url,
        'instagram_share_url': instagram_share_url,
    }

    return render(request, 'share_wrap.html', context)



def choice(request):
    """Determines the term selected by the user."""
    if request.method == "POST":
        term = request.POST.get("term")  # Get the term selected by the user
        if term in ["long", "medium", "short"]:  # Validate term
            request.session['term'] = term  # Store the term in the session
            return redirect("top_genre")  # Redirect to the 'top_genre' page
    return render(request, "spotifywrapper/choice.html")

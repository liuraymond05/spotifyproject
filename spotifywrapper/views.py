import random

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.utils import timezone
import datetime
import requests
import base64
from django.shortcuts import redirect
from django.utils.translation import get_language
from django.utils import translation
from django.http import HttpResponseRedirect
from spotifyproject.settings import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from .forms import PasswordResetCustomForm, CustomUserForm
from .models import SavedWrap, UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import activate
from django.shortcuts import render
from .spotify_helper import get_user_top_tracks, select_random_tracks

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
                # SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
                # CLIENT_ID = "0981ffa5b46448b4bda7f25862742556"
                # REDIRECT_URI = "http://127.0.0.1:8000/spotify/callback/"
                # SCOPES = "user-top-read"
                # auth_url = (
                #     f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={CLIENT_ID}"
                #     f"&redirect_uri={REDIRECT_URI}&scope={SCOPES}"
                # )
                # return redirect(auth_url)

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
            user_profile.token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
            user_profile.save()
            return redirect('home')

    print(f"Access token stored in session: {request.session.get('spotify_access_token')}")
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
            user_profile.token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
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
def settings(request):
    language_code = get_language()  # Use get_language to get the current language
    return render(request, 'settings.html', {
        'language_code': language_code
    })

@login_required
def delete_account(request):
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


def set_language(request, language_code):
    # Define supported languages
    supported_languages = ['en', 'es', 'fr', 'de']

    # If the language code is not supported, redirect back to the referring page or fallback to home
    if language_code not in supported_languages:
        return redirect(request.META.get('HTTP_REFERER', '/'))  # Redirect to previous page or home if unsupported

    # Activate the selected language
    activate(language_code)

    # Store the selected language in the session
    if hasattr(request, 'session'):
        request.session['django_language'] = language_code

    # Create the redirect response and set the language cookie
    response = HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    response.set_cookie('django_language', language_code)  # Store the selected language in the cookie

    return response
@login_required
def top_spotify_data(request):
    """
    View to get the user's top genre, top 3 artists, and minutes listened on Spotify and display them in the template.
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
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        username = profile_data.get('display_name', 'Unknown')  # Get the display name from the profile
    else:
        username = 'Unknown'

    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = request.GET.get('time_range', 'long_term')

    # Fetch the top artists (limit to 3) based on the selected time range
    top_artists_response = requests.get(
        f'https://api.spotify.com/v1/me/top/artists?time_range={time_range}&limit=3',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_artists_data = []
    if top_artists_response.status_code == 200:
        top_artists = top_artists_response.json()['items']
        for artist in top_artists:
            top_artists_data.append({
                'name': artist['name'],
                'image': artist['images'][0]['url'] if artist['images'] else None
            })
    else:
        return redirect('home')  # Redirect back if there was an error fetching top artists

    # Get the top genre (most frequent genre from top artists)
    genres = []
    for artist in top_artists:
        genres.extend(artist['genres'])

    top_genre = max(set(genres), key=genres.count) if genres else None

    # Get the minutes listened: sum the time of top tracks
    top_tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    total_minutes_listened = 0
    if top_tracks_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']
        total_minutes_listened = sum([track['duration_ms'] for track in top_tracks]) // 60000

    return render(request, 'spotifywrapper/wrapped.html', {
        'top_genre': top_genre,
        'top_artists': top_artists_data,
        'total_minutes_listened': total_minutes_listened,
        'selected_time_range': time_range,  # Pass the selected time range to the template
        'username': username  # Pass the username to the template
    })


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
def wraps(request):
    return render(request, 'savedwraps.html')


def save_wrap(request):
    """
    View that saves the user's spotify data into the SavedWrap model. 
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect(spotify_login)
    access_token = get_spotify_access_token(user_profile)
    time_range = request.POST.get('time_range', 'long_term')
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

    # Fetch other data (e.g., top tracks, playlists, mood)
    top_genre_data = get_top_genre(access_token)
    favorite_decade_data = get_favorite_decade(access_token)
    top_tracks_data = get_top_tracks_data(access_token)
    top_playlist_data = get_top_playlist_data(access_token)
    favorite_mood = get_favorite_mood_data(access_token)
    peak_hour = get_peak_hour_data(access_token)
    favorite_decade = get_favorite_decade(access_token)
    top_album_data = get_top_album(access_token, time_range)


    # Save the data to the SavedWrap model
    saved_wrap = SavedWrap(
        username=request.user.username,
        top_genre = top_genre_data,
        time_range=time_range,
        top_artists=top_artists_data,
        top_tracks=top_tracks_data,
        top_playlist=top_playlist_data['name'] if top_playlist_data else None,
        favorite_mood=get_favorite_mood_data(access_token),
        top_album = top_album_data,
        favorite_decade = favorite_decade_data,
        # Save other fields as necessary, e.g., top_genre, favorite_decade, etc.
    )
    saved_wrap.save()

    return redirect('savedwraps')   

def get_top_album(access_token, time_range):
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    # Fetch top tracks to get the album information
    url = f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=1'  # Using the top tracks endpoint

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['items']:
            # Fetch the album related to the top track
            top_track = data['items'][0]
            top_album = {
                'name': top_track['album']['name'],  # Album name
                'image': top_track['album']['images'][0]['url'],  # Album image URL
                'release_date': top_track['album']['release_date'],  # Release date of the album
                'details': top_track['album']['external_urls']['spotify'],  # Album's Spotify URL
            }
            return top_album
        else:
            return None
    else:
        return None


def get_peak_hour_data(access_token):
    """
    Helper function to determine the user's peak listening hour based on recently played tracks.
    """
    # Fetch the user's recently played tracks (limit to 50 for simplicity)
    tracks_response = requests.get(
        'https://api.spotify.com/v1/me/player/recently-played?limit=50',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    if tracks_response.status_code != 200:
        return None  # Return None if there's an error fetching tracks

    tracks_data = tracks_response.json().get('items', [])
    
    # Extract the timestamps of when the tracks were played
    played_hours = []
    for track in tracks_data:
        timestamp = track['played_at']
        played_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        played_hours.append(played_time.hour)

    # Count the occurrences of each hour (0-23)
    hour_count = Counter(played_hours)

    # Determine the peak hour (the hour with the most plays)
    peak_hour = max(hour_count, key=hour_count.get) if hour_count else None

    return peak_hour


def get_top_genre(access_token):
    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = 'long_term'  # You can modify this if needed to pass the time_range explicitly

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

def get_favorite_decade(access_token):
    top_tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=50',  # Increased limit to get more tracks
        headers={'Authorization': f'Bearer {access_token}'}
    )

    decades = []
    if top_tracks_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']
        for track in top_tracks:
            release_year = track['album']['release_date'][:4]  # Get the year from release_date
            decade = (int(release_year) // 10) * 10  # Round to nearest decade
            decades.append(decade)
    
    # Determine the most frequent decade
    favorite_decade = max(Counter(decades), key=Counter(decades).get) if decades else None
    
    return favorite_decade

def get_favorite_mood_data(access_token):
    """
    Helper function to determine the user's favorite mood based on Spotify's audio features.
    """
    # Fetch the user's top tracks
    tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=50',  # Fetch top 50 tracks
        headers={'Authorization': f'Bearer {access_token}'}
    )

    mood_count = {
        "Happy": 0,
        "Sad": 0,
        "Energetic": 0,
        "Relaxed": 0
    }
    favorite_mood = None

    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json().get('items', [])
        track_ids = [track['id'] for track in tracks_data]

        # Fetch audio features for the top tracks
        if track_ids:
            audio_features_response = requests.get(
                f'https://api.spotify.com/v1/audio-features?ids={",".join(track_ids)}',
                headers={'Authorization': f'Bearer {access_token}'}
            )

            if audio_features_response.status_code == 200:
                audio_features_data = audio_features_response.json().get('audio_features', [])
                for feature in audio_features_data:
                    if not feature:
                        continue

                    # Analyze track mood based on valence and energy
                    valence = feature.get('valence', 0)
                    energy = feature.get('energy', 0)

                    if valence >= 0.5 and energy >= 0.5:
                        mood_count["Happy"] += 1
                    elif valence < 0.5 and energy < 0.5:
                        mood_count["Sad"] += 1
                    elif valence < 0.5 and energy >= 0.5:
                        mood_count["Energetic"] += 1
                    elif valence >= 0.5 and energy < 0.5:
                        mood_count["Relaxed"] += 1

        # Determine the favorite mood
        favorite_mood = max(mood_count, key=mood_count.get)

    return favorite_mood


def get_top_tracks_data(access_token):
    response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    if response.status_code == 200:
        tracks = response.json().get('items', [])
        return [{'name': track['name'], 'artist': track['artists'][0]['name']} for track in tracks]
    return []

def get_top_playlist_data(access_token):
    response = requests.get(
        'https://api.spotify.com/v1/me/playlists?limit=1',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    if response.status_code == 200:
        playlists = response.json().get('items', [])
        if playlists:
            return {
                'name': playlists[0]['name'],
                'description': playlists[0].get('description', '')
            }
    return None




from django.shortcuts import render
from .models import SavedWrap

def saved_wraps(request):
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

from collections import Counter

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import base64
from django.shortcuts import redirect
from django.utils.translation import get_language
from django.utils import translation
from django.http import HttpResponseRedirect
from spotifyproject.settings import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from .forms import PasswordResetCustomForm, CustomUserForm
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import activate, get_language_from_request
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SavedWrap

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
def settings(request):
    language_code = request.LANGUAGE_CODE  # Use get_language to get the current language
    return render(request, 'settings.html', {
        'language_code': language_code,
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


def set_language(request):

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

    username = profile_response.json().get('display_name', 'Unknown') if profile_response.status_code == 200 else 'Unknown'


    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = request.GET.get('time_range', 'long_term')

    top_tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=3',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_tracks = []
    if top_tracks_response.status_code == 200:
        top_tracks = top_tracks_response.json()['items']

    top_tracks_data = []
    for track in top_tracks:
        top_tracks_data.append({
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'preview_url': track['preview_url']

        })


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
                'image': artist['images'][0]['url'] if 'images' in artist else None,
            })
    else:
        return redirect('home')  # Redirect back if there was an error fetching top artists


    recently_played_response = requests.get(
        'https://api.spotify.com/v1/me/player/recently-played?limit=50',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    recently_played_data = []
    recently_played_items = recently_played_response.json().get('items', [])
    listening_hours = Counter()
    for item in recently_played_items:
        played_at = item['played_at']
        played_hour = datetime.fromisoformat(played_at[:-1]).hour
        listening_hours[played_hour] += 1
    peak_hour = max(listening_hours, key=listening_hours.get)
    peak_hour_count = listening_hours[peak_hour]


    saved_tracks_response = requests.get(
        'https://api.spotify.com/v1/me/tracks?limit=1',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    saved_tracks_count = 0
    if saved_tracks_response.status_code == 200:
        saved_tracks_items = saved_tracks_response.json().get('total', 0)


    # Get the top genre (most frequent genre from top artists)
    genres = []
    for artist in top_artists:
        genres.extend(artist['genres'])

    top_genre = max(set(genres), key=genres.count) if genres else None

    # Top tracks for album and mood
    top_tracks_response = requests.get(
        f'https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=10',
        headers={'Authorization': f'Bearer {access_token}'}
    )

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


    valence_energy_map = {'Euphoric': 0, 'Chill': 0, 'Fiery': 0, 'Melancholic': 0}
    for track in top_tracks:
        valence = track['valence'] if 'valence' in track else 0.5
        energy = track['energy'] if 'energy' in track else 0.5
        if valence >= 0.5 and energy >= 0.5:
            valence_energy_map['Euphoric'] += 1
        elif valence >= 0.5 and energy < 0.5:
            valence_energy_map['Chill'] += 1
        elif valence < 0.5 and energy >= 0.5:
            valence_energy_map['Fiery'] += 1
        elif valence < 0.5 and energy < 0.5:
                valence_energy_map['Melancholic'] += 1

    favorite_mood = max(valence_energy_map, key=valence_energy_map.get)

    top_song = None
    if top_tracks:
        top_song = top_tracks[0]['name']

    # Get the most played playlist
    playlists_response = requests.get(
        'https://api.spotify.com/v1/me/playlists?limit=1',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    top_playlist = None
    if playlists_response.status_code == 200:
        playlists = playlists_response.json()['items']
        top_playlist = playlists[0]['name'] if playlists else None

    return render(request, 'spotifywrapper/wrapped.html', {
        'top_genre': top_genre,
        'top_artists': top_artists_data,
        'selected_time_range': time_range,  # Pass the selected time range to the template
        'top_song': top_song,
        'top_playlist': top_playlist,
        'username': username, # Pass the username to the template
        'favorite_decade': favorite_decade,
        'favorite_mood': favorite_mood,
        'peak_hour': peak_hour_count,
        'top_album': top_album,
        'top_tracks': top_tracks,
        'album_details': album_details,

    })

def gamepage(request):
    return render(request, 'games.html')
def wraps(request):
    return render(request, 'savedwraps.html')
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SavedWrap  # Assuming you have a SavedWrap model to store wrapped data

@csrf_exempt
def save_wrap(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = request.user

        # Save the wrapped data
        saved_wrap = SavedWrap(
            user=user,
            top_artists=data['top_artists'],
            top_tracks=data['top_tracks'],
            top_albums=data['top_albums'],
            minutes_listened=data['minutes_listened'],
            time_range=data['time_range'],
        )
        saved_wrap.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})
from django.shortcuts import render
from .models import SavedWrap

def saved_wraps(request):
    saved_wraps = SavedWrap.objects.filter(user=request.user)
    return render(request, 'spotifywrapper/savedwraps.html', {'saved_wraps': saved_wraps})


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

    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = request.GET.get('time_range', 'long_term')

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

    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = request.GET.get('time_range', 'long_term')

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

    # Get the time range selected by the user (default to 'long_term' if not provided)
    time_range = request.GET.get('time_range', 'long_term')

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

    # Fetch the user's top tracks
    tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=10',  # Fetch the top 10 tracks
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
    })

@login_required
def top_playlist(request):
    """
    View to display the user's top Spotify playlist based on the top Spotify data view.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if user is not authenticated with Spotify

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Fetch the user's playlists
    playlists_response = requests.get(
        'https://api.spotify.com/v1/me/playlists?limit=10',  # Fetch more playlists for context
        headers={'Authorization': f'Bearer {access_token}'}
    )

    top_playlist_data = None
    if playlists_response.status_code == 200:
        playlists = playlists_response.json().get('items', [])
        if playlists:
            top_playlist = playlists[0]  # Assume the first playlist is the "top" one
            top_playlist_data = {
                'name': top_playlist['name'],
                'description': top_playlist.get('description', ''),
                'image': top_playlist['images'][0]['url'] if top_playlist['images'] else None,
                'url': top_playlist['external_urls']['spotify'],
                'track_count': top_playlist['tracks']['total'],
            }

    return render(request, 'spotifywrapper/top-playlist.html', {
        'top_playlist': top_playlist_data,
    })

@login_required
def favorite_decade(request):
    """
    View to display the user's favorite decade based on Spotify data.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if Spotify is not authenticated

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Fetch the user's top tracks
    tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=50',  # Fetch the top 50 tracks for better analysis
        headers={'Authorization': f'Bearer {access_token}'}
    )

    decade_count = {}
    top_decade = None
    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json().get('items', [])
        for track in tracks_data:
            # Get the release year from the album's release date
            release_date = track['album']['release_date']
            if release_date:
                year = int(release_date[:4])
                decade = (year // 10) * 10  # Calculate the decade (e.g., 1980, 1990)
                decade_count[decade] = decade_count.get(decade, 0) + 1

        # Determine the top decade
        if decade_count:
            top_decade = max(decade_count, key=decade_count.get)

    # Format decade data for the template
    decade_data = [{'decade': decade, 'count': count} for decade, count in decade_count.items()]
    decade_data.sort(key=lambda x: x['decade'])  # Sort decades chronologically

    return render(request, 'spotifywrapper/favorite-decade.html', {
        'decade_data': decade_data,
        'top_decade': top_decade,
    })

@login_required
def favorite_mood(request):
    """
    View to determine the user's favorite mood based on Spotify data.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if Spotify is not authenticated

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

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

    # Format mood data for the template
    mood_data = [{'mood': mood, 'count': count} for mood, count in mood_count.items()]
    mood_data.sort(key=lambda x: x['mood'])

    return render(request, 'spotifywrapper/favorite-mood.html', {
        'mood_data': mood_data,
        'favorite_mood': favorite_mood,
    })

@login_required
def top_three_tracks(request):
    """
    View to display the top three tracks based on the user's Spotify data.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if Spotify is not authenticated

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Fetch the user's top tracks (limit to 3)
    tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=3',  # Fetch top 3 tracks
        headers={'Authorization': f'Bearer {access_token}'}
    )

    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json().get('items', [])
    else:
        tracks_data = []

    return render(request, 'spotifywrapper/top-three-tracks.html', {
        'tracks': tracks_data
    })


@login_required
def listening_habits(request):
    """
    View to display the listening habits of the user based on their Spotify data.
    This could include favorite genres, top tracks, and top artists.
    """
    user_profile = UserProfile.objects.filter(user=request.user).first()
    if not user_profile or not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect if Spotify is not authenticated

    # Get the access token
    access_token = get_spotify_access_token(user_profile)

    # Fetch the user's top tracks (limit to 5 for variety)
    tracks_response = requests.get(
        'https://api.spotify.com/v1/me/top/tracks?limit=5',  # Top 5 tracks
        headers={'Authorization': f'Bearer {access_token}'}
    )

    # Fetch the user's top artists (limit to 5 for variety)
    artists_response = requests.get(
        'https://api.spotify.com/v1/me/top/artists?limit=5',  # Top 5 artists
        headers={'Authorization': f'Bearer {access_token}'}
    )

    # Fetch the user's top genres (this might require additional processing)
    genres_response = requests.get(
        'https://api.spotify.com/v1/me/top/artists?limit=50',  # Get more artists to infer genres
        headers={'Authorization': f'Bearer {access_token}'}
    )

    if tracks_response.status_code == 200:
        tracks_data = tracks_response.json().get('items', [])
    else:
        tracks_data = []

    if artists_response.status_code == 200:
        artists_data = artists_response.json().get('items', [])
    else:
        artists_data = []

    if genres_response.status_code == 200:
        genres_data = genres_response.json().get('items', [])
        # Process genres from artists (as genres are not directly available in the user data)
        genres = set()
        for artist in genres_data:
            genres.update(artist['genres'])
        genres_data = list(genres)  # Get unique genres
    else:
        genres_data = []

    return render(request, 'spotifywrapper/listening-habits.html', {
        'tracks': tracks_data,
        'artists': artists_data,
        'genres': genres_data
    })
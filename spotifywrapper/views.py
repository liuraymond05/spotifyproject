from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
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
from .models import UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import activate

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
            user_profile.token_expires = timezone.now() + datetime.timedelta(seconds=expires_in)
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


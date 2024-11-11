from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
import datetime
import requests
from .models import UserProfile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm


def login_view(request):
    """Handles user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
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
def home(request):
    """Renders the home page after login and Spotify authentication."""
    return render(request, 'home.html')


# Spotify API credentials and URLs
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"



def spotify_login(request):
    """Initiates Spotify login and authorization flow."""
    if not request.user.is_authenticated:
        return redirect('login')

    user_profile = UserProfile.objects.filter(user=request.user).first()

    # If user doesn't have a valid Spotify token, start the authentication flow
    if user_profile is None or not user_profile.spotify_access_token:
        scope = "user-top-read user-read-recently-played user-library-read"
        auth_url = (
            f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={SPOTIFY_CLIENT_ID}"

        )
        return redirect(auth_url)

    return redirect('home')


def spotify_callback(request):
    """Handles Spotify's callback with the authorization code."""
    code = request.GET.get('code')
    if code:
        # Exchange the authorization code for an access token
        token_response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,

                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            },
        )
        token_data = token_response.json()

        # Check if we have the access and refresh tokens
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

        messages.error(request, "Spotify authentication failed. Missing tokens.")
        return redirect('login')

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

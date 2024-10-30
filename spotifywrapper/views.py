from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.contrib.auth import logout
from .forms import CustomUserForm, PasswordResetCustomForm
from django.contrib.auth.models import User
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
import requests

from .models import UserProfile

sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        scope="user-top-read"
    )
# Create your views here.
#Views for the spotify login and authorization
def spotify_login(request):
    print(f"Current user: {request.user}, Authenticated: {request.user.is_authenticated}")

    if not request.user.is_authenticated:
        # Redirect to login or handle unauthenticated users
        return redirect('login')

    user_profile = UserProfile.objects.filter(user=request.user).first()
    if user_profile is None:
        print(f"No UserProfile found for user: {request.user.id}")  # Debug info
        auth_url = sp_oauth.get_authorize_url()
        print("Redirecting to Spotify authorization...")
        return redirect(auth_url)

    if user_profile.spotify_access_token:
        print("Redirecting to home...")
        return redirect('home')

    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

'''
#View for the top 10 songs
def spotify_callback(request):
    sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        scope="user-top-read"
    )
    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    top_tracks = sp.current_user_top_tracks(limit=10)
    return render(request, 'spotifywrapper/top_tracks.html', {'top_tracks': top_tracks})
'''


def spotify_callback(request):
    code = request.GET.get('code')
    if code:
        token_info = sp_oauth.get_access_token(code)
        if token_info:
            access_token = token_info['access_token']
            refresh_token = token_info['refresh_token']
            user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
            user_profile.spotify_access_token = access_token
            user_profile.spotify_refresh_token = refresh_token
            user_profile.save()
            print("Redirecting to home")
            return redirect('home')

    # If no code or token retrieval failed, handle as necessary
    print("Token retrieval failed or no code")
    return redirect('login')  # or another error page

#Handle the user login
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('spotify_login')  # Redirect to home after login
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    return render(request, 'spotifywrapper/login.html')

# Handle user logout
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have successfully logged out!')
        return redirect('login')
    return render(request, 'spotifywrapper/logout.html')

# Handle user registration
def register_view(request):
    form = CustomUserForm()

    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create a UserProfile for the new user
            UserProfile.objects.create(user=user)
            messages.success(request, 'You have successfully created an account!')
            return redirect('login')
    else:
        messages.error(request, 'Please complete the entire form.')
    return render(request, 'spotifywrapper/register.html', {'form': form})

#Handle resetting a user's password
def reset_password_view(request):
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


def home(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Check if the access token is available
    if not user_profile.spotify_access_token:
        return redirect('spotify_login')  # Redirect to login if token not found

    sp = spotipy.Spotify(auth=user_profile.spotify_access_token)

    # Fetch user's top tracks
    top_tracks = sp.current_user_top_tracks(limit=10)
    top_tracks_list = [{"name": track['name'], "artists": ", ".join([artist['name'] for artist in track['artists']])}
                       for track in top_tracks['items']]

    # Fetch user's top artists
    top_artists = sp.current_user_top_artists(limit=10)
    top_artists_list = [{"name": artist['name'], "genres": ", ".join(artist['genres'])} for artist in
                        top_artists['items']]

    # Prepare context for rendering
    context = {
        'year': 2024,
        'top_songs': top_tracks_list,
        'top_artists': top_artists_list,
        'total_minutes_listened': 1500,  # Placeholder
        'stars_rating': 5,  # Static rating for simplicity
    }

    return render(request, 'spotifywrapper/home.html', context)

def get_spotify_data(request):
    # Get access token from Spotify
    url = "https://accounts.spotify.com/api/token"
    data = {
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data, auth=(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET))
    access_token = response.json().get("access_token")

    # Fetch top artists
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    top_artists_response = requests.get("https://api.spotify.com/v1/me/top/artists?limit=3", headers=headers)
    top_artists = top_artists_response.json().get("items", [])

    # Fetch top songs
    top_tracks_response = requests.get("https://api.spotify.com/v1/me/top/tracks?limit=3", headers=headers)
    top_tracks = top_tracks_response.json().get("items", [])

    # Fetch top albums (this requires you to know how to get top albums,
    # since Spotify does not provide a direct endpoint for this)
    # Here, you can loop through the top artists and get their albums.
    top_albums = []
    for artist in top_artists:
        artist_id = artist['id']
        albums_response = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}/albums?limit=3",
                                       headers=headers)
        top_albums.extend(albums_response.json().get("items", [])[:3])  # Get top 3 albums for each artist

    # Simulate minutes listened. You may replace this with actual data from your user account.
    minutes_listened = 1200  # Replace this with actual data as needed

    context = {
        'top_artists': top_artists,
        'top_tracks': top_tracks,
        'top_albums': top_albums,
        'minutes_listened': minutes_listened,
    }

    return render(request, 'your_template.html', context)



def game_home(request):
    # Placeholder view for game home
    return HttpResponse("Welcome to the Game Home Page")

def get_user_top_tracks(request):
    # Placeholder view for user top tracks
    return HttpResponse("Here are your top tracks")
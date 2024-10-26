from django.shortcuts import render
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from django.shortcuts import redirect, render

# Create your views here.
#Views for the spotify login and authorization
def spotify_login(request):
    sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        scope="user-top-read"
    )
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
    return render(request, 'spotify/top_tracks.html', {'top_tracks': top_tracks})


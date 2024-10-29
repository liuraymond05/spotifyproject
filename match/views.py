from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import redirect
import urllib.parse
import os
import requests

def spotify_login(request):
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    scope = "user-top-read"  # Define permissions for the app, e.g., access to top tracks

    # Build the Spotify Authorization URL
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
    })
    return redirect(auth_url)

def spotify_callback(request):
    code = request.GET.get("code")  # Get code from redirect URI
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    # Request an access token from Spotify
    token_url = "https://accounts.spotify.com/api/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    response = requests.post(token_url, data=token_data)
    response_data = response.json()

    access_token = response_data.get("access_token")
    # Store or pass this token to the rest of your app as needed
    # For example, save it in the session or database for future requests

    return redirect('game_home')  # Redirect to another page in your app

def game_home(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return redirect('spotify_login')
    return render(request, 'game_home.html')

def get_user_top_tracks(request):
    # Step 1: Check for access token in the session
    access_token = request.session.get('access_token')
    if not access_token:
        # Redirect to login if there is no access token
        return redirect('spotify_login')

    # Step 2: Define the Spotify API endpoint for top tracks
    endpoint = "https://api.spotify.com/v1/me/top/tracks"

    # Step 3: Set up headers with the access token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 4: Make the GET request to Spotify's API
    response = requests.get(endpoint, headers=headers)
    if response.status_code != 200:
        return JsonResponse({"error": "Failed to retrieve top tracks"}, status=response.status_code)

    # Step 5: Parse and return the response data
    data = response.json()
    return JsonResponse(data)  # Return the top tracks as JSON for now
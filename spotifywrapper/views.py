from django.shortcuts import render, redirect
from django.contrib import messages, auth
from django.contrib.auth import logout
from .forms import CustomUserForm, PasswordResetCustomForm
from django.contrib.auth.models import User
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings



# Create your views here.
#Views for the spotify login and authorization
def spotify_login(request):
    sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        scope="user-top-read"
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

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
            form.save()
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

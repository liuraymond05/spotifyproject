from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from . import views  # Import views from the current directory

urlpatterns = [
    # URL pattern for the login page
    path('', views.login_view, name='login'),

    # URL pattern for the home page
    path('home/', views.home, name='home'),

    # URL pattern for initiating Spotify login
    path('spotify/login/', views.spotify_login, name='spotify_login'),

    # URL pattern for the Spotify callback after successful login
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),

    # URL pattern for the user choice page
    path('choice/', views.choice, name='choice'),

    # URL pattern for the login page (duplicate of the first one, may need removal)
    path('login/', views.login_view, name='login'),

    # URL pattern for logging out the user
    path('logout/', views.logout_view, name='logout'),

    # URL pattern for the user registration page
    path('register/', views.register_view, name='register'),

    # URL pattern for resetting the password
    path('reset/', views.reset_password_view, name='reset'),

    # URL pattern for obtaining Spotify access token
    path('spotify/access/', views.get_spotify_access_token, name='get_spotify_access_token'),

    # URL pattern for fetching the user's Spotify profile
    path('spotify/profile/', views.get_spotify_profile, name='get_spotify_profile'),

    # URL pattern for refreshing the Spotify access token
    path('spotify/refresh/', views.refresh_spotify_token, name='refresh_spotify_token'),

    # URL pattern for user settings page
    path('settings/', views.user_settings, name='settings'),

    # URL pattern for deleting the user account
    path('delete-account/', views.delete_account, name='delete_account'),

    # URL pattern for contacting the developers
    path('contact-developers/', views.contact_developers, name='contact_developers'),

    # URL pattern for setting the user's language preference
    path('set_language/', views.set_language, name='set_language'),

    # URL pattern for the wrapped page, displaying user’s Spotify data
    path('wrapped/', views.top_spotify_data, name='wrapped'),

    # URL pattern for accessing top Spotify data
    path('top_spotify_data', views.top_spotify_data, name='top_spotify_data'),

    # URL pattern for the game page
    path('game/', views.gamepage, name='game'),

    # URL pattern for displaying the user's saved Spotify wraps
    path('wraps', views.wraps, name='wraps'),

    # URL pattern for saving the wrap data
    path('save_wrap/', views.save_wrap, name='save_wrap'),

    # URL pattern for sharing a wrap
    path('share_wrap/', views.share_wrap, name='share_wrap'),

    # URL pattern for viewing saved wraps
    path('savedwraps/', views.saved_wraps, name='savedwraps'),

    # URL pattern for viewing the user's top genre
    path('top-genre/', views.top_genre, name='top_genre'),

    # URL pattern for viewing the user's top songs
    path('top-songs/', views.top_songs, name='top_songs'),

    # URL pattern for viewing the user's top artists
    path('top-artists/', views.top_artists, name='top_artists'),

    # URL pattern for viewing the user’s playlist element
    path('top-playlist/', views.user_element, name='top_playlist'),

    # URL pattern for viewing the user's top albums
    path('top-albums/', views.top_albums, name='top_albums'),

    # URL pattern for viewing the user's favorite decade
    path('favorite-decade/', views.favorite_decade, name='favorite_decade'),

    # URL pattern for viewing the top three tracks
    path('top-three-tracks/', views.top_three_tracks, name='top_three_tracks'),

    # URL pattern for ending the wrapped session
    path('end_wrapped/', views.end_wrapped, name='end_wrapped'),

    # URL pattern for viewing the user's favorite mood (popularity level)
    path('favorite-mood/', views.popularity_level, name='favorite_mood'),

    # URL pattern for viewing the user's listening habits
    path('listening-habits/', views.listening_habits, name='listening_habits'),

    # URL pattern for deleting a specific wrap
    path('delete_wrap/<int:wrap_id>/', views.delete_wrap, name='delete_wrap'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

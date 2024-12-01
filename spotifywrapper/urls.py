from django.urls import path
from . import views  # Import views from the current directory

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('choice/', views.choice, name='choice'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('reset/', views.reset_password_view, name='reset'),
    path('spotify/access/', views.get_spotify_access_token, name='get_spotify_access_token'),
    path('spotify/profile/', views.get_spotify_profile, name='get_spotify_profile'),
    path('spotify/refresh/', views.refresh_spotify_token, name='refresh_spotify_token'),
    path('settings/', views.settings, name='settings'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('contact-developers/', views.contact_developers, name='contact_developers'),
    path('set_language/', views.set_language, name='set_language'),
    path('wrapped/', views.top_spotify_data, name='wrapped'),
    path('top_spotify_data', views.top_spotify_data, name='top_spotify_data'),
    path('gamepage', views.gamepage, name='gamepage'),
    path('wraps', views.wraps, name='wraps'),
    path('save_wrap/', views.save_wrap, name='save_wrap'),
    path('savedwraps/', views.saved_wraps, name='savedwraps'),
    path('top-genre/', views.top_genre, name='top_genre'),
    path('top-songs/', views.top_songs, name='top_songs'),
    path('top-artists/', views.top_artists, name='top_artists'),
    path('top-playlist/', views.top_playlist, name='top_playlist'),
    path('top-albums/', views.top_albums, name='top_albums'),
    path('favorite-decade/', views.favorite_decade, name='favorite_decade'),
    path('top-three-tracks/', views.top_three_tracks, name='top_three_tracks'),
    path('favorite-mood/', views.favorite_mood, name='favorite_mood'),
    path('listening-habits/', views.listening_habits, name='listening_habits'),
    path('delete_wrap/<int:wrap_id>/', views.delete_wrap, name='delete_wrap'),



]

from django.urls import path
from . import views  # Import views from the current directory

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
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
    path('top-songs/', views.top_songs, name='top_songs'),
    path('top-artists/', views.top_artists, name='top_artists'),
    path('top-albums/', views.top_albums, name='top_albums'),
    path('minutes-listened/', views.minutes_listened, name='minutes_listened'),



]

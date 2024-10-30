from django.urls import path
from spotifywrapper import views

urlpatterns = [
    path('login/spotify/', views.spotify_login, name='spotify_login'),
    path('callback/spotify/', views.spotify_callback, name='spotify_callback'),
    path('game/home/', views.game_home, name='game_home'),
    path('user/top-tracks/', views.get_user_top_tracks, name='get_user_top_tracks'),
]

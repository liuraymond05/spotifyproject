from django.urls import path

from spotifyproject.urls import urlpatterns
from. import views

urlpatterns = [
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
]
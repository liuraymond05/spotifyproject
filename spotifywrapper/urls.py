from django.urls import path, include
from . import views
from .views import get_spotify_data

urlpatterns = [
    path('home/', views.home, name='home'),
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('reset/', views.reset_password_view, name='reset'),
    path('spotify/', get_spotify_data, name='spotify_data'),
]


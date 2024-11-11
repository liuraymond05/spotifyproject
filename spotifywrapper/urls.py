from django.urls import path
from . import views  # Import views from the current directory

urlpatterns = [
    path('home/', views.home, name='home'),
    path('spotify/login/', views.spotify_login, name='spotify_login'),
    path('spotify/callback/', views.spotify_callback, name='spotify_callback'),
    path('login/', views.login_view, name='login'),  # Ensure you have a login view
    path('logout/', views.logout_view, name='logout'),  # Ensure you have a logout view
]

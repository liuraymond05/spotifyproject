from django.db import models
from django.contrib.auth.models import User
from django.shortcuts import redirect


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    spotify_access_token = models.CharField(max_length=255, blank=True, null=True)
    spotify_refresh_token = models.CharField(max_length=255, blank=True, null=True)
    token_expires = models.DateTimeField(blank=True, null=True)


def __str__(self):
        return self.user.username


def register_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)

        # Create UserProfile
        UserProfile.objects.create(user=user)
        # Other registration logic...

        return redirect('login')  # Redirect to login after registration



class SavedWrap(models.Model):
    username = models.CharField(max_length=100)
    time_range = models.CharField(max_length=50)
    top_genre = models.CharField(max_length=100)
    top_artists = models.JSONField()  # Storing as JSON to handle lists
    top_tracks = models.JSONField()

    def __str__(self):
        return f"{self.username} - {self.time_range}"

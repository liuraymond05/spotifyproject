from django.db import models
from django.contrib.auth.models import User
from django.shortcuts import redirect


class UserProfile(models.Model):
    """
    Model to store additional information about a user related to their Spotify account.

    This model extends the `User` model to store the Spotify access token, refresh token, 
    and the expiration time of the access token for each user.

    Attributes:
        user (OneToOneField): The user associated with this profile. This creates a one-to-one relationship
                               with the Django User model.
        spotify_access_token (CharField): The access token used for authenticating with Spotify API.
        spotify_refresh_token (CharField): The refresh token used to obtain a new access token when it expires.
        token_expires (DateTimeField): The expiration date and time of the Spotify access token.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    spotify_access_token = models.CharField(max_length=255, blank=True, null=True)
    spotify_refresh_token = models.CharField(max_length=255, blank=True, null=True)
    token_expires = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        """
        String representation of the UserProfile.

        Returns:
            str: The username of the associated user.
        """
        return self.user.username


def register_user(request):
    """
    Handles the user registration process.

    This function processes the POST request to create a new user, generates a new `UserProfile` for the user,
    and redirects to the login page after successful registration.

    Args:
        request (HttpRequest): The HTTP request object containing form data for registration.
    
    Returns:
        HttpResponse: A redirect response to the login page after registration.
    """
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)

        # Create UserProfile
        UserProfile.objects.create(user=user)
        # Other registration logic...

        return redirect('login')  # Redirect to login after registration


class SavedWrap(models.Model):
    """
    Model to store the user's Spotify data, including their top artists, tracks, genres, and more.

    This model saves a "wrapped" summary of the user's Spotify usage over a specified time range.

    Attributes:
        username (CharField): The username of the user whose Spotify data is saved.
        time_range (CharField): The time range for which the data is saved (e.g., 'short_term', 'medium_term', 'long_term').
        top_genre (CharField): The user's most listened-to genre.
        top_album (CharField): The user's most listened-to album.
        top_artists (JSONField): A list of the user's top artists (stored as JSON).
        top_tracks (JSONField): A list of the user's top tracks (stored as JSON).
        top_song (CharField): The user's top song.
        user_element (CharField): An associated "element" based on the user's favorite genres.
        favorite_decade (CharField): The user's favorite decade based on their music preferences.
        top_song_popularity (CharField): The popularity of the user's top song (e.g., 'High', 'Medium', 'Low').
    """
    username = models.CharField(max_length=100)
    time_range = models.CharField(max_length=50)
    top_genre = models.CharField(max_length=100, null=True, blank=True)
    top_album = models.CharField(max_length=100, null=True, blank=True)
    top_artists = models.JSONField(default=list, blank=True)  # Storing as JSON to handle lists
    top_tracks = models.JSONField(default=list, blank=True)
    top_song = models.CharField(max_length=100, null=True, blank=True)
    user_element = models.CharField(max_length=100, null=True, blank=True)
    favorite_decade = models.CharField(max_length=100, null=True, blank=True)
    top_song_popularity = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        """
        String representation of the SavedWrap.

        Returns:
            str: A string containing the username and time range associated with the saved Spotify wrap.
        """
        return f"{self.username} - {self.time_range}"
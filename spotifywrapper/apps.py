from django.apps import AppConfig


class SpotifywrapperConfig(AppConfig):
    """
    Configuration class for the 'spotifywrapper' Django application.

    This class provides the application-specific configuration for the Spotifywrapper app.
    It defines the default auto field type and the name of the app within the Django project.

    Attributes:
        default_auto_field (str): The default field type for auto-generated primary keys. 
        name (str): The name of the Django application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'spotifywrapper'
# Generated by Django 5.1.2 on 2024-11-30 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spotifywrapper', '0006_alter_savedwrap_top_artists_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedwrap',
            name='top_album',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]

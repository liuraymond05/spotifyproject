# Generated by Django 5.1.2 on 2024-11-30 07:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spotifywrapper', '0003_savedwrap'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='savedwrap',
            name='minutes_listened',
        ),
        migrations.RemoveField(
            model_name='savedwrap',
            name='top_albums',
        ),
        migrations.RemoveField(
            model_name='savedwrap',
            name='user',
        ),
        migrations.AddField(
            model_name='savedwrap',
            name='top_genre',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='savedwrap',
            name='username',
            field=models.CharField(default='anonymous', max_length=100),
            preserve_default=False,
        ),
    ]

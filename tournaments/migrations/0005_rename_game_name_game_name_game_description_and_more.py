# Generated by Django 5.0.7 on 2024-08-11 21:35

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0004_rename_location_game_game_name_remove_game_team1_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='game',
            old_name='game_name',
            new_name='name',
        ),
        migrations.AddField(
            model_name='game',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='team',
            name='access_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name='team',
            name='team_number',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name='team',
            name='members',
        ),
        migrations.AddField(
            model_name='team',
            name='members',
            field=models.TextField(default=2),
            preserve_default=False,
        ),
    ]

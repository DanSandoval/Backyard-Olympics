# Generated by Django 5.0.7 on 2024-08-09 17:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0003_remove_game_date_remove_tournament_end_date_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='game',
            old_name='location',
            new_name='game_name',
        ),
        migrations.RemoveField(
            model_name='game',
            name='team1',
        ),
        migrations.RemoveField(
            model_name='game',
            name='team2',
        ),
        migrations.RemoveField(
            model_name='game',
            name='winner',
        ),
    ]
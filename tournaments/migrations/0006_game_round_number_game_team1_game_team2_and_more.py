import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0005_rename_game_name_game_name_game_description_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='round_number',
            field=models.IntegerField(null=True),  # Allow nulls temporarily
        ),
        migrations.AddField(
            model_name='game',
            name='team1',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='home_games',
                to='tournaments.Team'
            ),
        ),
        migrations.AddField(
            model_name='game',
            name='team2',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='away_games',
                to='tournaments.Team'
            ),
        ),
        migrations.AlterField(
            model_name='game',
            name='name',
            field=models.CharField(max_length=255),
        ),
    ]

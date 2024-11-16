# Generated by Django 5.0.7 on 2024-11-16 01:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0009_team_email_1_team_email_2_team_phone_number_1_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('MATCHUP', 'Matchup Update'), ('ROUND', 'Round Update'), ('CONFLICT', 'Conflict Alert'), ('SYSTEM', 'System Message')], max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')], default='MEDIUM', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('related_matchup', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='tournaments.matchup')),
                ('related_round', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='tournaments.round')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='tournaments.team')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TournamentStanding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wins', models.IntegerField(default=0)),
                ('losses', models.IntegerField(default=0)),
                ('wager_points', models.IntegerField(default=0)),
                ('total_points', models.IntegerField(default=0)),
                ('rank', models.IntegerField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='standings', to='tournaments.team')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='standings', to='tournaments.tournament')),
            ],
            options={
                'ordering': ['-total_points', '-wager_points'],
                'unique_together': {('tournament', 'team')},
            },
        ),
    ]
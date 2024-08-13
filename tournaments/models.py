from django.db import models
import uuid

class Tournament(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Team(models.Model):
    name = models.CharField(max_length=100)
    tournament = models.ForeignKey(Tournament, related_name='teams', on_delete=models.CASCADE)
    members = models.TextField()  # Storing members as a simple text field
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Unique identifier for QR code access
    team_number = models.IntegerField(null=True, blank=True)  # Placeholder for team number (1 to n)

    def __str__(self):
        return self.name

class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    team1 = models.ForeignKey(Team, related_name='home_games', on_delete=models.CASCADE, null=True, blank=True)
    team2 = models.ForeignKey(Team, related_name='away_games', on_delete=models.CASCADE, null=True, blank=True)
    round_number = models.IntegerField(null=True, blank=True)
    tournament = models.ForeignKey(Tournament, related_name='games', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.team1.name} vs {self.team2.name} - Round {self.round_number}"

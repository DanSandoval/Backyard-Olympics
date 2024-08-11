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
    name = models.CharField(max_length=100)  # Name of the game
    tournament = models.ForeignKey(Tournament, related_name='games', on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)  # Optional field for game description

    def __str__(self):
        return self.name

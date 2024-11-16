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

# models.py - Game model update

class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    team1 = models.ForeignKey(Team, related_name='home_games', on_delete=models.CASCADE, null=True, blank=True)
    team2 = models.ForeignKey(Team, related_name='away_games', on_delete=models.CASCADE, null=True, blank=True)
    round_number = models.IntegerField(null=True, blank=True)
    tournament = models.ForeignKey(Tournament, related_name='games', on_delete=models.CASCADE)
    
    # New fields
    winner = models.ForeignKey(
        Team, 
        related_name='games_won', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    score_team1 = models.IntegerField(null=True, blank=True)
    score_team2 = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('SCHEDULED', 'Scheduled'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed')
        ],
        default='SCHEDULED'
    )
    date_played = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.team1.name if self.team1 else 'TBD'} vs {self.team2.name if self.team2 else 'TBD'} - Round {self.round_number}"
    
    def determine_winner(self):
        if self.score_team1 is not None and self.score_team2 is not None:
            if self.score_team1 > self.score_team2:
                self.winner = self.team1
            elif self.score_team2 > self.score_team1:
                self.winner = self.team2
            self.status = 'COMPLETED'
            self.save()
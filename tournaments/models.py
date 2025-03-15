from django.db import models
import uuid

class Tournament(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
    def current_round(self):
        """Return the current active round, or None if no rounds are active"""
        rounds = self.rounds.filter(is_current=True)
        if rounds.exists():
            return rounds.first()
        return None

class Team(models.Model):
    name = models.CharField(max_length=100)
    tournament = models.ForeignKey(Tournament, related_name='teams', on_delete=models.CASCADE)
    members = models.TextField()  # Storing members as a simple text field
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Unique identifier for QR code access
    team_number = models.IntegerField(null=True, blank=True)  # Placeholder for team number (1 to n)
    
    # Additional contact information
    phone_number_1 = models.CharField(max_length=20, blank=True, null=True)
    phone_number_2 = models.CharField(max_length=20, blank=True, null=True)
    email_1 = models.EmailField(blank=True, null=True)
    email_2 = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name
    
    def get_wins(self):
        """Return the number of wins for this team"""
        # For backward compatibility, check both Game and Matchup
        old_wins = self.games_won.count()
        
        # New wins from Matchup
        new_wins_as_team1 = self.matchups_as_team1.filter(result='TEAM1_WIN').count()
        new_wins_as_team2 = self.matchups_as_team2.filter(result='TEAM2_WIN').count()
        
        return old_wins + new_wins_as_team1 + new_wins_as_team2

# Original Game model with minimal modifications
class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    rules = models.TextField(blank=True, null=True)  # New field
    team1 = models.ForeignKey(Team, related_name='home_games', on_delete=models.CASCADE, null=True, blank=True)
    team2 = models.ForeignKey(Team, related_name='away_games', on_delete=models.CASCADE, null=True, blank=True)
    round_number = models.IntegerField(null=True, blank=True)
    tournament = models.ForeignKey(Tournament, related_name='games', on_delete=models.CASCADE)
    
    # Existing fields
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

# New models below
class Round(models.Model):
    tournament = models.ForeignKey(Tournament, related_name='rounds', on_delete=models.CASCADE)
    round_number = models.IntegerField()
    start_time = models.DateTimeField(null=True, blank=True)
    length_minutes = models.IntegerField(default=30)  # Default 30 minutes per round
    is_current = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['round_number']
        unique_together = ['tournament', 'round_number']
    
    def __str__(self):
        return f"Round {self.round_number} - {self.tournament.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one round is current for a tournament
        if self.is_current:
            Round.objects.filter(tournament=self.tournament, is_current=True).exclude(id=self.id).update(is_current=False)
        super().save(*args, **kwargs)

class Matchup(models.Model):
    RESULT_CHOICES = [
        ('PENDING', 'Pending'),
        ('TEAM1_WIN', 'Team 1 Win'),
        ('TEAM2_WIN', 'Team 2 Win'),
    ]
    
    game = models.ForeignKey(Game, related_name='matchups', on_delete=models.CASCADE)
    round = models.ForeignKey(Round, related_name='matchups', on_delete=models.CASCADE)
    team1 = models.ForeignKey(Team, related_name='matchups_as_team1', on_delete=models.CASCADE, null=True, blank=True)
    team2 = models.ForeignKey(Team, related_name='matchups_as_team2', on_delete=models.CASCADE, null=True, blank=True)
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='PENDING')
    
    # Fields for conflict tracking
    conflict_flag = models.BooleanField(default=False)
    team1_reported_win = models.BooleanField(null=True, blank=True)
    team2_reported_win = models.BooleanField(null=True, blank=True)
    conflict_notes = models.TextField(blank=True, null=True)
    
    # BYE handling - if team2 is None, team1 has a bye
    is_bye = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['round', 'team1', 'team2']
    
    def __str__(self):
        if self.is_bye:
            return f"{self.game.name} - {self.team1.name} BYE - Round {self.round.round_number}"
        return f"{self.game.name} - {self.team1.name if self.team1 else 'TBD'} vs {self.team2.name if self.team2 else 'TBD'} - Round {self.round.round_number}"
    
    def save(self, *args, **kwargs):
        # Set is_bye to True if team2 is None but team1 isn't
        if self.team1 and not self.team2:
            self.is_bye = True
        super().save(*args, **kwargs)

class Wager(models.Model):
    team = models.ForeignKey(Team, related_name='wagers', on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name='wagers', on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['team', 'game']
    
    def __str__(self):
        return f"{self.team.name} - {self.game.name}: {self.points} points"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Check if team's total wager points equal 100
        total_points = Wager.objects.filter(team=self.team).exclude(pk=self.pk).aggregate(
            total=models.Sum('points'))['total'] or 0
        total_points += self.points
        
        if total_points > 100:
            raise ValidationError(f"Total wager points exceed 100. Current total: {total_points}")

class Notification(models.Model):
    tournament = models.ForeignKey(Tournament, related_name='notifications', on_delete=models.CASCADE)
    team = models.ForeignKey(Team, related_name='notifications', on_delete=models.CASCADE, null=True, blank=True)  # If None, sent to all teams
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.team:
            return f"{self.title} - {self.team.name}"
        return f"{self.title} - All Teams"
from django.db import models
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum
from django.utils import timezone

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
    phone_number_1 = models.CharField(max_length=20, blank=True, null=True)
    phone_number_2 = models.CharField(max_length=20, blank=True, null=True)
    email_1 = models.EmailField(blank=True, null=True)
    email_2 = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

# In models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Round(models.Model):
    tournament = models.ForeignKey('Tournament', related_name='rounds', on_delete=models.CASCADE)
    round_number = models.PositiveIntegerField()
    start_time = models.DateTimeField(null=True, blank=True)
    length_minutes = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['round_number']
        unique_together = [['tournament', 'round_number']]
        
    def clean(self):
        # Ensure length_minutes is positive
        if self.length_minutes <= 0:
            raise ValidationError({'length_minutes': 'Round length must be positive'})
        
        # Ensure no overlapping rounds in the same tournament
        if self.start_time:
            end_time = self.start_time + timezone.timedelta(minutes=self.length_minutes)
            overlapping_rounds = Round.objects.filter(
                tournament=self.tournament,
                start_time__lt=end_time,
                start_time__gt=self.start_time
            ).exclude(pk=self.pk)
            
            if overlapping_rounds.exists():
                raise ValidationError('Round overlaps with existing rounds')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def end_time(self):
        if self.start_time:
            return self.start_time + timezone.timedelta(minutes=self.length_minutes)
        return None
    
    @property
    def is_completed(self):
        if self.end_time:
            return timezone.now() > self.end_time
        return False
    
    def __str__(self):
        return f"Round {self.round_number} - {self.tournament.name}"

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

class Matchup(models.Model):
    game = models.ForeignKey(Game, related_name='matchups', on_delete=models.CASCADE)
    round = models.ForeignKey(Round, related_name='matchups', on_delete=models.CASCADE)
    team_1 = models.ForeignKey(Team, related_name='team_1_matchups', on_delete=models.CASCADE)
    team_2 = models.ForeignKey(Team, related_name='team_2_matchups', on_delete=models.CASCADE, null=True, blank=True)  # Null for byes
    result_entered_by = models.ForeignKey(Team, related_name='results_entered', on_delete=models.SET_NULL, null=True, blank=True)
    result_confirmed = models.BooleanField(default=False)
    conflict_flag = models.BooleanField(default=False)
    winner = models.ForeignKey(Team, related_name='matchups_won', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = [['round', 'team_1'], ['round', 'team_2']]
        
    def __str__(self):
        team2_name = self.team_2.name if self.team_2 else "BYE"
        return f"{self.game.name}: {self.team_1.name} vs {team2_name} (Round {self.round.round_number})"

class Wager(models.Model):
    team = models.ForeignKey(Team, related_name='wagers', on_delete=models.CASCADE)
    game = models.ForeignKey(Game, related_name='wagers', on_delete=models.CASCADE)
    points = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        unique_together = ['team', 'game']

    def clean(self):
        # Ensure total team wagers don't exceed 100
        total_points = Wager.objects.filter(team=self.team).exclude(pk=self.pk).aggregate(
            total=Sum('points'))['total'] or 0
        if total_points + self.points > 100:
            raise ValidationError('Total wager points cannot exceed 100')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.team.name} wagered {self.points} on {self.game.name}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('MATCHUP', 'Matchup Update'),
        ('ROUND', 'Round Update'),
        ('CONFLICT', 'Conflict Alert'),
        ('SYSTEM', 'System Message'),
    ]

    PRIORITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]

    team = models.ForeignKey(Team, related_name='notifications', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='MEDIUM')
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    related_matchup = models.ForeignKey('Matchup', null=True, blank=True, on_delete=models.SET_NULL)
    related_round = models.ForeignKey('Round', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']

    def mark_as_read(self):
        self.read_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.title} - {self.team.name}"

class TournamentStanding(models.Model):
    tournament = models.ForeignKey(Tournament, related_name='standings', on_delete=models.CASCADE)
    team = models.ForeignKey(Team, related_name='standings', on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    wager_points = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_points', '-wager_points']
        unique_together = ['tournament', 'team']

    def __str__(self):
        return f"{self.team.name} - Rank {self.rank or 'TBD'}"

    def calculate_points(self):
        """Calculate total points based on wins and wager points"""
        self.total_points = (self.wins * 100) + self.wager_points
        self.save()
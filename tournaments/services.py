from django.db import transaction
from django.db.models import F, Count
from django.utils import timezone
from .models import Tournament, Team, Game, Round, Matchup, Notification, TournamentStanding, Wager
from typing import List, Dict, Tuple
from django.db.models import Q
from datetime import datetime

class TournamentScheduler:
    def __init__(self, tournament):
        self.tournament = tournament
        
    @transaction.atomic
    def generate_schedule(self, round_length_minutes=45):
        """
        Generates a complete tournament schedule with rounds and matchups.
        Each team plays each game exactly once.
        """
        teams = list(self.tournament.teams.all())
        games = list(self.tournament.games.all())
        
        # Calculate number of rounds needed
        num_teams = len(teams)
        num_games = len(games)
        matches_per_round = num_teams // 2
        total_rounds = num_games  # Each team plays each game once
        
        # Create rounds
        rounds = []
        start_time = timezone.now().replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
        
        for round_num in range(1, total_rounds + 1):
            round = Round.objects.create(
                tournament=self.tournament,
                round_number=round_num,
                start_time=start_time,
                length_minutes=round_length_minutes
            )
            rounds.append(round)
            start_time += timezone.timedelta(minutes=round_length_minutes)
            
        # Generate matchups for each round
        for round_idx, round in enumerate(rounds):
            game = games[round_idx]  # Each round focuses on one game
            available_teams = teams.copy()
            
            while len(available_teams) >= 2:
                team1 = available_teams.pop(0)
                team2 = available_teams.pop(0)
                
                Matchup.objects.create(
                    game=game,
                    round=round,
                    team_1=team1,
                    team_2=team2
                )
                
            # Handle bye if odd number of teams
            if available_teams:
                Matchup.objects.create(
                    game=game,
                    round=round,
                    team_1=available_teams[0],
                    team_2=None  # Bye
                )
                
    def adjust_round_timing(self, round, new_start_time):
        """
        Adjusts the timing of a round and all subsequent rounds
        """
        affected_rounds = Round.objects.filter(
            tournament=self.tournament,
            round_number__gte=round.round_number
        ).order_by('round_number')
        
        current_time = new_start_time
        for r in affected_rounds:
            r.start_time = current_time
            r.save()
            current_time += timezone.timedelta(minutes=r.length_minutes) 

class NotificationService:
    @staticmethod
    def create_matchup_notification(matchup, message, priority='MEDIUM'):
        """Create notifications for both teams in a matchup"""
        teams = [matchup.team_1, matchup.team_2] if matchup.team_2 else [matchup.team_1]
        
        for team in teams:
            Notification.objects.create(
                team=team,
                type='MATCHUP',
                title=f'Update for {matchup.game.name}',
                message=message,
                priority=priority,
                related_matchup=matchup
            )

    @staticmethod
    def create_round_notification(round, message, priority='MEDIUM'):
        """Create notifications for all teams in a round"""
        teams = Team.objects.filter(tournament=round.tournament)
        
        notifications = [
            Notification(
                team=team,
                type='ROUND',
                title=f'Round {round.round_number} Update',
                message=message,
                priority=priority,
                related_round=round
            )
            for team in teams
        ]
        
        Notification.objects.bulk_create(notifications)

    @staticmethod
    def create_conflict_notification(matchup, message):
        """Create conflict notifications for involved teams and tournament admin"""
        teams = [matchup.team_1, matchup.team_2]
        
        for team in teams:
            Notification.objects.create(
                team=team,
                type='CONFLICT',
                title='Score Conflict',
                message=message,
                priority='HIGH',
                related_matchup=matchup
            )

class StandingsService:
    @staticmethod
    @transaction.atomic
    def update_standings(tournament):
        """Update standings for all teams in a tournament"""
        # Get all confirmed matchups
        confirmed_matchups = Matchup.objects.filter(
            tournament=tournament,
            result_confirmed=True
        )

        # Calculate wins and losses
        wins_by_team = confirmed_matchups.values('winner').annotate(
            win_count=Count('winner')
        )

        # Create a dictionary for quick lookup
        wins_dict = {item['winner']: item['win_count'] for item in wins_by_team if item['winner']}

        # Update or create standings for each team
        teams = tournament.teams.all()
        for team in teams:
            # Calculate wager points from confirmed matchups
            wager_points = 0
            for matchup in confirmed_matchups.filter(winner=team):
                wager = Wager.objects.filter(team=team, game=matchup.game).first()
                if wager:
                    wager_points += wager.points

            standing, created = TournamentStanding.objects.update_or_create(
                tournament=tournament,
                team=team,
                defaults={
                    'wins': wins_dict.get(team.id, 0),
                    'losses': confirmed_matchups.filter(
                        models.Q(team_1=team) | models.Q(team_2=team)
                    ).exclude(winner=team).count(),
                    'wager_points': wager_points
                }
            )
            standing.calculate_points()

        # Update rankings
        standings = TournamentStanding.objects.filter(
            tournament=tournament
        ).order_by('-total_points', '-wager_points')

        for rank, standing in enumerate(standings, 1):
            standing.rank = rank
            standing.save()

    @staticmethod
    def get_team_standing(team):
        """Get current standing for a specific team"""
        return TournamentStanding.objects.filter(team=team).first() 

class SchedulingService:
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.teams = list(tournament.teams.all())
        self.games = list(tournament.games.all())
        self.num_teams = len(self.teams)
        self.num_games = len(self.games)
        
    def validate_tournament_setup(self) -> Tuple[bool, str]:
        """
        Validates that the tournament has the necessary components for scheduling.
        Returns (is_valid, error_message)
        """
        if not self.teams:
            return False, "No teams registered for tournament"
        if not self.games:
            return False, "No games defined for tournament"
        if self.num_teams < 2:
            return False, "Need at least 2 teams for tournament"
        return True, ""

    def calculate_rounds_needed(self) -> int:
        """
        Calculates the number of rounds needed for Phase 1.
        Each team must play each game exactly once.
        """
        return self.num_games

    def get_optimal_bye_distribution(self) -> Dict[int, Team]:
        """
        Creates a fair bye distribution when there's an odd number of teams.
        Returns a dictionary mapping round numbers to teams that get byes.
        """
        bye_rounds = {}
        if self.num_teams % 2 == 1:
            teams_cycle = self.teams.copy()
            for round_num in range(1, self.calculate_rounds_needed() + 1):
                # Rotate teams for fair bye distribution
                bye_team = teams_cycle.pop(0)
                teams_cycle.append(bye_team)
                bye_rounds[round_num] = bye_team
        return bye_rounds

    def generate_round_pairings(self, round_number: int, available_teams: List[Team]) -> List[Tuple[Team, Team]]:
        """
        Generates fair pairings for a single round, considering previous matchups.
        """
        pairings = []
        teams = available_teams.copy()
        
        # Shuffle teams to randomize matchups while maintaining fairness
        import random
        random.shuffle(teams)
        
        while len(teams) >= 2:
            team1 = teams.pop(0)
            # Find the best opponent for team1 (one they haven't played yet if possible)
            best_opponent_idx = 0
            for i, potential_opponent in enumerate(teams):
                # Check if these teams have played each other before
                previous_matchup = Matchup.objects.filter(
                    tournament=self.tournament,
                    round__round_number__lt=round_number
                ).filter(
                    (Q(team_1=team1, team_2=potential_opponent) |
                     Q(team_1=potential_opponent, team_2=team1))
                ).exists()
                
                if not previous_matchup:
                    best_opponent_idx = i
                    break
            
            team2 = teams.pop(best_opponent_idx)
            pairings.append((team1, team2))
        
        return pairings

    @transaction.atomic
    def generate_phase1_schedule(self, round_length_minutes: int = 45) -> bool:
        """
        Generates the complete Phase 1 schedule ensuring:
        1. Each team plays each game exactly once
        2. Byes are distributed fairly
        3. No team plays the same opponent twice if avoidable
        """
        # Validate tournament setup
        is_valid, error_message = self.validate_tournament_setup()
        if not is_valid:
            raise ValueError(error_message)

        # Calculate rounds needed
        total_rounds = self.calculate_rounds_needed()
        
        # Get bye distribution
        bye_rounds = self.get_optimal_bye_distribution()
        
        # Calculate start time for first round
        start_time = timezone.now().replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
        
        # Create rounds
        for round_num in range(1, total_rounds + 1):
            # Create the round
            current_round = Round.objects.create(
                tournament=self.tournament,
                round_number=round_num,
                start_time=start_time,
                length_minutes=round_length_minutes
            )
            
            # Get teams available for this round (excluding bye team)
            available_teams = [team for team in self.teams if team != bye_rounds.get(round_num)]
            
            # Generate pairings for this round
            pairings = self.generate_round_pairings(round_num, available_teams)
            
            # Create matchups for this round
            game = self.games[round_num - 1]  # Each round focuses on one game
            
            for team1, team2 in pairings:
                Matchup.objects.create(
                    tournament=self.tournament,
                    round=current_round,
                    game=game,
                    team_1=team1,
                    team_2=team2
                )
            
            # Handle bye if necessary
            if bye_team := bye_rounds.get(round_num):
                Matchup.objects.create(
                    tournament=self.tournament,
                    round=current_round,
                    game=game,
                    team_1=bye_team,
                    team_2=None  # Indicates a bye
                )
            
            # Update start time for next round
            start_time += timezone.timedelta(minutes=round_length_minutes)
        
        return True

    def validate_schedule(self) -> List[str]:
        """
        Validates the generated schedule against requirements.
        Returns a list of any violations found.
        """
        violations = []
        
        # Check that each team plays each game exactly once
        for team in self.teams:
            for game in self.games:
                game_count = Matchup.objects.filter(
                    tournament=self.tournament,
                    game=game
                ).filter(
                    Q(team_1=team) | Q(team_2=team)
                ).count()
                
                if game_count != 1:
                    violations.append(
                        f"Team {team.name} plays {game.name} {game_count} times (should be 1)"
                    )
        
        # Check for consecutive byes
        for team in self.teams:
            rounds = Round.objects.filter(tournament=self.tournament).order_by('round_number')
            previous_was_bye = False
            
            for round in rounds:
                matchup = Matchup.objects.filter(
                    round=round
                ).filter(
                    Q(team_1=team) | Q(team_2=team)
                ).first()
                
                is_bye = matchup and matchup.team_2 is None
                
                if is_bye and previous_was_bye:
                    violations.append(f"Team {team.name} has consecutive byes")
                
                previous_was_bye = is_bye
        
        return violations

    def adjust_round_timing(self, round_number: int, new_start_time: datetime) -> bool:
        """
        Adjusts the timing of a specific round and all subsequent rounds.
        Returns True if successful, False if the adjustment would create conflicts.
        """
        try:
            with transaction.atomic():
                affected_rounds = Round.objects.filter(
                    tournament=self.tournament,
                    round_number__gte=round_number
                ).order_by('round_number')
                
                if not affected_rounds.exists():
                    return False
                
                current_start = new_start_time
                for round in affected_rounds:
                    round.start_time = current_start
                    round.save()
                    current_start += timezone.timedelta(minutes=round.length_minutes)
                
                return True
        except Exception as e:
            print(f"Error adjusting round timing: {e}")
            return False 
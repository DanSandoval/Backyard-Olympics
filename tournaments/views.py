from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import transaction
from django.db.models import Sum, Count
from django.contrib import messages
from django.utils import timezone

from .models import Tournament, Team, Game, Round, Matchup, Wager, Notification
from .forms import TournamentForm, TeamForm, GameForm, RoundForm, MatchupForm, WagerForm, NotificationForm

def home(request):
    return render(request, 'home.html')

@login_required
def choose_create_tournament(request):
    tournaments = Tournament.objects.all()
    return render(request, 'choose_create_tournament.html', {'tournaments': tournaments})

@login_required
def create_tournament(request):
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save()
            return redirect('select_tournament', tournament.pk)
    else:
        form = TournamentForm()
    return render(request, 'tournament_form.html', {'form': form})

@login_required
def select_tournament(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    return redirect('tournament_review', tournament_id=tournament.pk)

@login_required
def add_teams(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.tournament = tournament
            team.save()
            return redirect('add_teams', tournament_id=tournament.pk)
    else:
        form = TeamForm()
    return render(request, 'add_teams.html', {'form': form, 'tournament': tournament})

@login_required
def add_games(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            game = form.save(commit=False)
            game.tournament = tournament
            game.save()
            return redirect('add_games', tournament_id=tournament.pk)
    else:
        form = GameForm()
    return render(request, 'add_games.html', {'form': form, 'tournament': tournament})

@login_required
def tournament_review(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams_with_numbers = tournament.teams.filter(team_number__isnull=False).exists()
    
    # Get current round if it exists
    current_round = tournament.current_round()
    
    # Get active notifications
    notifications = Notification.objects.filter(tournament=tournament, is_read=False)

    return render(request, 'tournament_review.html', {
        'tournament': tournament,
        'teams_with_numbers': teams_with_numbers,
        'current_round': current_round,
        'notifications': notifications
    })

@login_required
def team_list(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all()

    if request.method == 'POST':
        if 'add_team' in request.POST:
            form = TeamForm(request.POST)
            if form.is_valid():
                team = form.save(commit=False)
                team.tournament = tournament
                team.team_number = None  # Placeholder for team number to be assigned later

                # Process members from the comma-separated string
                members = form.cleaned_data['members']
                member_names = [name.strip() for name in members.split(',')]
                team.members = ', '.join(member_names)  # Store members as a comma-separated string

                team.save()
                return redirect('team_list', tournament_id=tournament.pk)
        elif 'remove_team' in request.POST:
            team_id = request.POST.get('team_id')
            if team_id.isdigit():  # Ensure the ID is numeric
                team = get_object_or_404(Team, pk=team_id, tournament=tournament)
                team.delete()
                return redirect('team_list', tournament_id=tournament.pk)

    else:
        form = TeamForm()

    return render(request, 'tournaments/team_list.html', {'tournament': tournament, 'teams': teams, 'form': form})

@login_required
def game_list(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    games = tournament.games.all()

    if request.method == 'POST':
        if 'add_game' in request.POST:
            form = GameForm(request.POST)
            if form.is_valid():
                game = form.save(commit=False)
                game.tournament = tournament
                game.save()
                return redirect('game_list', tournament_id=tournament.pk)
        elif 'remove_game' in request.POST:
            game_id = request.POST.get('game_id')
            if game_id.isdigit():
                game = get_object_or_404(Game, pk=game_id, tournament=tournament)
                game.delete()
                return redirect('game_list', tournament_id=tournament.pk)

    else:
        form = GameForm()

    return render(request, 'tournaments/game_list.html', {'tournament': tournament, 'games': games, 'form': form})

@login_required
def tournament_begins(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    # If the tournament has already begun (has rounds), redirect to review
    if tournament.rounds.exists():
        return redirect('review_entries', tournament_id=tournament.pk)
    
    if request.method == 'POST':
        # Assign team numbers
        teams = list(tournament.teams.all())
        for i, team in enumerate(teams):
            team.team_number = i + 1
            team.save()
        
        # Create rounds
        num_teams = len(teams)
        required_rounds = num_teams - 1 if num_teams % 2 == 0 else num_teams
        
        # Create first round as current
        first_round = Round.objects.create(
            tournament=tournament,
            round_number=1,
            start_time=timezone.now(),
            is_current=True
        )
        
        # Create remaining rounds
        for i in range(2, required_rounds + 1):
            Round.objects.create(
                tournament=tournament,
                round_number=i,
                is_current=False
            )
            
        # Generate matchups for first round
        generate_matchups_for_round(tournament, first_round)
        
        messages.success(request, "Tournament has begun! First round is in progress.")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    return render(request, 'tournament_begins.html', {'tournament': tournament})

@login_required
def finalize_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all()
    games = tournament.games.all()

    if request.method == 'POST':
        # Finalize the tournament and assign teams
        if not teams.filter(team_number__isnull=False).exists():
            for i, team in enumerate(teams):
                team.team_number = i + 1
                team.save()

        # Create first round
        first_round = Round.objects.create(
            tournament=tournament,
            round_number=1,
            start_time=timezone.now(),
            is_current=True
        )
        
        # Generate matchups
        generate_matchups_for_round(tournament, first_round)

        return redirect('review_entries', tournament_id=tournament.pk)

    return render(request, 'finalize_tournament.html', {
        'tournament': tournament,
        'teams': teams,
        'games': games
    })

def generate_matchups_for_round(tournament, round_obj):
    """Generate matchups for a specific round using round-robin scheduling"""
    teams = list(tournament.teams.all())
    games = list(tournament.games.all())
    
    # If odd number of teams, add a bye (None)
    if len(teams) % 2 != 0:
        teams.append(None)
    
    # Round-robin algorithm
    n = len(teams)
    matchups = []
    
    # For the given round_number, calculate the matchups
    round_num = round_obj.round_number
    
    # Fixed position team
    fixed = teams[0]
    
    # Rotating teams
    rotating = teams[1:]
    
    # Rotate (round_num - 1) times to get current round matchups
    for _ in range(round_num - 1):
        rotating.insert(0, rotating.pop())
    
    # Create matchups for this round
    half = n // 2
    
    # Assign games in a round-robin fashion
    game_index = 0
    num_games = len(games)
    
    # Fixed team vs first rotating
    if fixed and rotating[0]:  # Both are actual teams (not None for bye)
        game = games[game_index % num_games]
        game_index += 1
        Matchup.objects.create(
            game=game,
            round=round_obj,
            team1=fixed,
            team2=rotating[0],
            is_bye=False
        )
    elif fixed:  # rotating[0] is None, fixed team gets a bye
        game = games[game_index % num_games]
        game_index += 1
        Matchup.objects.create(
            game=game,
            round=round_obj,
            team1=fixed,
            team2=None,
            is_bye=True
        )
    
    # Rest of the teams
    for i in range(1, half):
        team1 = rotating[i]
        team2 = rotating[n-1-i]
        
        if team1 and team2:  # Both are actual teams
            game = games[game_index % num_games]
            game_index += 1
            Matchup.objects.create(
                game=game,
                round=round_obj,
                team1=team1,
                team2=team2,
                is_bye=False
            )
        elif team1:  # team2 is None, team1 gets a bye
            game = games[game_index % num_games]
            game_index += 1
            Matchup.objects.create(
                game=game,
                round=round_obj,
                team1=team1,
                team2=None,
                is_bye=True
            )
        elif team2:  # team1 is None, team2 gets a bye
            game = games[game_index % num_games]
            game_index += 1
            Matchup.objects.create(
                game=game,
                round=round_obj,
                team1=team2,
                team2=None,
                is_bye=True
            )

@login_required
def generate_matchups(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    if request.method == 'POST':
        # Clear existing matchups and rounds
        tournament.rounds.all().delete()
        
        teams = list(tournament.teams.all())
        games = list(tournament.games.all())
        
        # Check if there are enough teams and games
        if len(teams) < 2 or len(games) == 0:
            messages.error(request, "Need at least 2 teams and 1 game to create matchups")
            return redirect('review_entries', tournament_id=tournament.pk)
        
        # Create rounds
        num_teams = len(teams)
        required_rounds = num_teams - 1 if num_teams % 2 == 0 else num_teams
        
        # Create first round as current
        first_round = Round.objects.create(
            tournament=tournament,
            round_number=1,
            start_time=timezone.now(),
            is_current=True
        )
        
        # Create remaining rounds
        for i in range(2, required_rounds + 1):
            Round.objects.create(
                tournament=tournament,
                round_number=i,
                is_current=False
            )
            
        # Generate matchups for all rounds
        rounds = tournament.rounds.all().order_by('round_number')
        for round_obj in rounds:
            generate_matchups_for_round(tournament, round_obj)
        
        messages.success(request, f"Generated matchups for {required_rounds} rounds")
        
    return redirect('review_entries', tournament_id=tournament.pk)

@login_required
def review_entries(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all().order_by('team_number')
    
    # Get current round and its matchups
    current_round = tournament.current_round()
    
    if current_round:
        matchups = current_round.matchups.all()
        games = tournament.games.all()
        rounds = tournament.rounds.all().order_by('round_number')
    else:
        matchups = []
        games = tournament.games.all()
        rounds = []

    return render(request, 'review_entries.html', {
        'tournament': tournament,
        'teams': teams,
        'games': games,
        'current_round': current_round,
        'matchups': matchups,
        'rounds': rounds
    })

@login_required
def print_grids(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    rounds = tournament.rounds.all().order_by('round_number')
    teams = tournament.teams.all().order_by('team_number')
    
    # Generate grid data
    grid_data = []
    for round_obj in rounds:
        matchups = round_obj.matchups.all()
        round_data = {
            'round': round_obj,
            'matchups': matchups
        }
        grid_data.append(round_data)
    
    if request.method == 'POST':
        # This would be where you generate a PDF or printable version
        # For now, we'll just return the same template
        messages.info(request, "Grid printing functionality will be implemented in a future update")
    
    return render(request, 'print_grids.html', {
        'tournament': tournament,
        'grid_data': grid_data,
        'teams': teams
    })

@login_required
def input_results(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    current_round = tournament.current_round()
    
    if not current_round:
        messages.error(request, "No active round found")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    matchups = current_round.matchups.all()
    
    if request.method == 'POST':
        for matchup in matchups:
            winner_key = f'winner_{matchup.id}'
            if winner_key in request.POST:
                winner_id = request.POST.get(winner_key)
                if winner_id:
                    if int(winner_id) == matchup.team1.id:
                        matchup.result = 'TEAM1_WIN'
                    elif matchup.team2 and int(winner_id) == matchup.team2.id:
                        matchup.result = 'TEAM2_WIN'
                    matchup.save()
        
        messages.success(request, "Results saved successfully")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    return render(request, 'input_results.html', {
        'tournament': tournament,
        'current_round': current_round,
        'matchups': matchups
    })

@login_required
def reset_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    if request.method == 'POST':
        # Remove all matchups and rounds
        tournament.rounds.all().delete()
        
        # Reset team numbers
        teams = tournament.teams.all()
        for team in teams:
            team.team_number = None
            team.save()
        
        messages.success(request, "Tournament has been reset")
    
    return redirect('review_entries', tournament_id=tournament.pk)

# New views for the enhanced system

@login_required
def next_round(request, tournament_id):
    """Advance to the next round"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    current_round = tournament.current_round()
    
    if not current_round:
        messages.error(request, "No active round found")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    # Find the next round
    next_round = Round.objects.filter(
        tournament=tournament,
        round_number__gt=current_round.round_number
    ).order_by('round_number').first()
    
    if not next_round:
        messages.info(request, "This is already the last round")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    # Update current round flag
    with transaction.atomic():
        current_round.is_current = False
        current_round.save()
        
        next_round.is_current = True
        next_round.start_time = timezone.now()
        next_round.save()
    
    messages.success(request, f"Advanced to Round {next_round.round_number}")
    return redirect('review_entries', tournament_id=tournament.pk)

@login_required
def previous_round(request, tournament_id):
    """Go back to the previous round"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    current_round = tournament.current_round()
    
    if not current_round:
        messages.error(request, "No active round found")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    # Find the previous round
    prev_round = Round.objects.filter(
        tournament=tournament,
        round_number__lt=current_round.round_number
    ).order_by('-round_number').first()
    
    if not prev_round:
        messages.info(request, "This is already the first round")
        return redirect('review_entries', tournament_id=tournament.pk)
    
    # Update current round flag
    with transaction.atomic():
        current_round.is_current = False
        current_round.save()
        
        prev_round.is_current = True
        prev_round.save()
    
    messages.success(request, f"Returned to Round {prev_round.round_number}")
    return redirect('review_entries', tournament_id=tournament.pk)

@login_required
def manage_wagers(request, tournament_id, team_id=None):
    """Manage wagers for a team"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    if team_id:
        team = get_object_or_404(Team, pk=team_id, tournament=tournament)
        games = tournament.games.all()
        
        # Get existing wagers
        wagers = Wager.objects.filter(team=team)
        wager_dict = {w.game.id: w for w in wagers}
        
        if request.method == 'POST':
            # Process wager form
            total_points = 0
            wager_data = {}
            
            # Validate total points = 100
            for game in games:
                points_key = f'points_{game.id}'
                if points_key in request.POST:
                    try:
                        points = int(request.POST[points_key])
                        if points < 0:
                            messages.error(request, f"Points for {game.name} cannot be negative")
                            return redirect('manage_wagers', tournament_id=tournament.pk, team_id=team.pk)
                        
                        total_points += points
                        wager_data[game.id] = points
                    except ValueError:
                        messages.error(request, f"Invalid points value for {game.name}")
                        return redirect('manage_wagers', tournament_id=tournament.pk, team_id=team.pk)
            
            if total_points != 100:
                messages.error(request, f"Total points must equal 100 (got {total_points})")
                return redirect('manage_wagers', tournament_id=tournament.pk, team_id=team.pk)
            
            # Save wagers
            with transaction.atomic():
                for game_id, points in wager_data.items():
                    game = Game.objects.get(pk=game_id)
                    if game_id in wager_dict:
                        # Update existing wager
                        wager = wager_dict[game_id]
                        wager.points = points
                        wager.save()
                    else:
                        # Create new wager
                        Wager.objects.create(team=team, game_id=game_id, points=points)
            
            messages.success(request, "Wagers saved successfully")
            return redirect('review_entries', tournament_id=tournament.pk)
        
        # Create a dict of game_id -> points for the form
        game_points = {g.id: wager_dict.get(g.id).points if g.id in wager_dict else 0 for g in games}
        
        return render(request, 'manage_wagers.html', {
            'tournament': tournament,
            'team': team,
            'games': games,
            'game_points': game_points,
            'total_points': sum(game_points.values())
        })
    
    # No team_id provided, show list of teams
    teams = tournament.teams.all().order_by('team_number')
    return render(request, 'select_team_for_wagers.html', {
        'tournament': tournament,
        'teams': teams
    })

@login_required
def conflict_resolution(request, tournament_id):
    """View and resolve matchup conflicts"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    # Get all matchups with conflicts
    conflict_matchups = Matchup.objects.filter(
        round__tournament=tournament,
        conflict_flag=True
    ).order_by('round__round_number')
    
    if request.method == 'POST':
        # Process conflict resolution
        matchup_id = request.POST.get('matchup_id')
        resolution = request.POST.get('resolution')
        
        if matchup_id and resolution:
            matchup = get_object_or_404(Matchup, pk=matchup_id, round__tournament=tournament)
            
            if resolution == 'team1':
                matchup.result = 'TEAM1_WIN'
            elif resolution == 'team2':
                matchup.result = 'TEAM2_WIN'
            
            matchup.conflict_flag = False
            matchup.conflict_notes = f"Resolved by admin on {timezone.now()}"
            matchup.save()
            
            messages.success(request, "Conflict resolved successfully")
            return redirect('conflict_resolution', tournament_id=tournament.pk)
    
    return render(request, 'conflict_resolution.html', {
        'tournament': tournament,
        'conflict_matchups': conflict_matchups
    })

@login_required
def report_result(request, tournament_id, matchup_id):
    """Team reporting a matchup result"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    matchup = get_object_or_404(Matchup, pk=matchup_id, round__tournament=tournament)
    
    # In a real implementation, we'd verify the team access token here
    # For now, we'll just use a simple form
    
    if request.method == 'POST':
        winner_id = request.POST.get('winner_id')
        team_reporting = request.POST.get('team_reporting')
        
        if not winner_id or not team_reporting:
            messages.error(request, "Missing required information")
            return redirect('report_result', tournament_id=tournament.pk, matchup_id=matchup.pk)
        
        # Process the result
        if team_reporting == 'team1':
            matchup.team1_reported_win = (winner_id == str(matchup.team1.id))
        elif team_reporting == 'team2' and matchup.team2:
            matchup.team2_reported_win = (winner_id == str(matchup.team2.id))
        
        # Check if results match
        if matchup.team1_reported_win is not None and matchup.team2_reported_win is not None:
            if matchup.team1_reported_win == matchup.team2_reported_win:
                # Both teams agree
                if matchup.team1_reported_win:
                    matchup.result = 'TEAM1_WIN'
                else:
                    matchup.result = 'TEAM2_WIN'
                matchup.conflict_flag = False
            else:
                # Conflict - teams disagree
                matchup.conflict_flag = True
                matchup.conflict_notes = "Teams reported different winners"
        
        matchup.save()
        
        if matchup.conflict_flag:
            messages.warning(request, "Result conflict detected. An admin will review.")
        else:
            messages.success(request, "Result reported successfully")
        
        return redirect('review_entries', tournament_id=tournament.pk)
    
    return render(request, 'report_result.html', {
        'tournament': tournament,
        'matchup': matchup
    })

@login_required
def create_notification(request, tournament_id):
    """Create a new notification"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all()
    
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.tournament = tournament
            
            # Handle "all teams" checkbox
            all_teams = form.cleaned_data.get('all_teams')
            if all_teams:
                notification.team = None  # Indicates all teams
            
            notification.save()
            messages.success(request, "Notification created successfully")
            return redirect('review_entries', tournament_id=tournament.pk)
    else:
        form = NotificationForm()
    
    return render(request, 'create_notification.html', {
        'tournament': tournament,
        'form': form,
        'teams': teams
    })

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, pk=notification_id)
    tournament_id = notification.tournament.id
    
    notification.is_read = True
    notification.save()
    
    return redirect('review_entries', tournament_id=tournament_id)

@login_required
def tournament_standings(request, tournament_id):
    """View the current tournament standings"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all().order_by('team_number')
    
    # Get win counts for each team
    team_stats = []
    for team in teams:
        # Get wins from traditional games (for backward compatibility)
        old_wins = team.games_won.count()
        
        # Get wins from matchups
        matchup_wins_as_team1 = team.matchups_as_team1.filter(result='TEAM1_WIN').count()
        matchup_wins_as_team2 = team.matchups_as_team2.filter(result='TEAM2_WIN').count()
        
        # Total wins
        total_wins = old_wins + matchup_wins_as_team1 + matchup_wins_as_team2
        
        # Get wager total (for tie-breaking)
        wager_points = Wager.objects.filter(team=team).aggregate(total=Sum('points'))['total'] or 0
        
        team_stats.append({
            'team': team,
            'wins': total_wins,
            'wager_points': wager_points
        })
    
    # Sort by wins (descending), then by wager points (descending)
    team_stats.sort(key=lambda x: (-x['wins'], -x['wager_points']))
    
    return render(request, 'tournament_standings.html', {
        'tournament': tournament,
        'team_stats': team_stats
    })
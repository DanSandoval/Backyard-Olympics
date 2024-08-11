from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import Tournament, Team, Game
from .forms import TournamentForm, TeamForm, GameForm

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
            form.save_m2m()
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
    return render(request, 'tournament_review.html', {'tournament': tournament})

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
    if request.method == 'POST':
        # Generate team numbers
        teams = list(tournament.teams.all())
        for i, team in enumerate(teams):
            team.number = i + 1
            team.save()
        # Redirect to review entries
        return redirect('review_entries', tournament_id=tournament.pk)
    return render(request, 'tournament_begins.html', {'tournament': tournament})

@login_required
def review_entries(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all()
    games = tournament.games.all()
    return render(request, 'review_entries.html', {'tournament': tournament, 'teams': teams, 'games': games})

@login_required
def print_grids(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        # Logic to print or download grids
        return redirect('review_entries', tournament_id=tournament.pk)
    return render(request, 'print_grids.html', {'tournament': tournament})

@login_required
def input_results(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    games = tournament.games.all()
    if request.method == 'POST':
        for game in games:
            winner_id = request.POST.get(f'winner_{game.id}')
            if winner_id:
                game.winner_id = winner_id
                game.save()
        return redirect('review_entries', tournament_id=tournament.pk)
    return render(request, 'input_results.html', {'tournament': tournament, 'games': games})


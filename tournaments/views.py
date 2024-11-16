from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import UpdateView, DetailView, ListView
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import HttpResponse
import qrcode
import qrcode.image.svg
from io import BytesIO
from django.db import transaction
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods

from .models import Tournament, Team, Game, Matchup, Round, Wager, TournamentStanding, Notification
from .forms import TournamentForm, TeamForm, GameForm
from .services import TournamentScheduler, SchedulingService, NotificationService

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
    
    teams = list(tournament.teams.all())
    num_teams = len(teams)
    rounds = []
    
    # Assign team numbers and shuffle
    for i, team in enumerate(teams):
        team.team_number = i + 1
        team.save()
    
    if num_teams % 2 != 0:
        teams.append(None)  # Add a bye (None represents a bye)
        num_teams += 1

    for round_number in range(num_teams - 1):
        round_games = []
        for i in range(num_teams // 2):
            team1 = teams[i]
            team2 = teams[-(i + 1)]

            if team1 is None or team2 is None:
                # Bye logic
                if team1:
                    game = Game.objects.create(tournament=tournament, team1=team1, team2=None, round_number=round_number + 1)
                elif team2:
                    game = Game.objects.create(tournament=tournament, team1=team2, team2=None, round_number=round_number + 1)
            else:
                game = Game.objects.create(tournament=tournament, team1=team1, team2=team2, round_number=round_number + 1)
            
            round_games.append(game)

        rounds.append(round_games)
        teams.insert(1, teams.pop())  # Rotate teams except the first one
    
    # Redirect to review entries
    return redirect('review_entries', tournament_id=tournament.pk)


@login_required
def finalize_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all()

    # Finalize the tournament and assign teams
    if not teams.filter(team_number__isnull=False).exists():
        for i, team in enumerate(teams):
            team.team_number = i + 1
            team.save()

        # Generate matchups and schedule here (you can call another view or function)
        generate_matchups(tournament_id)

    return redirect('review_entries', tournament_id=tournament.pk)


@login_required
def generate_matchups(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = list(tournament.teams.all())
    games = list(tournament.games.all())

    # Clear any existing matchups
    games.clear()
    Game.objects.filter(tournament=tournament).delete()

    # Check if there are enough teams to generate matchups
    if len(teams) < 2:
        return redirect('review_entries', tournament_id=tournament.pk)

    # Generate Round-Robin Schedule
    schedule = generate_round_robin_schedule(teams)

    # Create games based on the schedule
    for round_number, round_games in enumerate(schedule, start=1):
        for team1, team2 in round_games:
            game_name = f"Game {round_number}"
            description = f"{team1.name} vs {team2.name}" if team2 else f"{team1.name} has a bye"
            Game.objects.create(
                name=game_name,
                description=description,
                team1=team1,
                team2=team2,
                round_number=round_number,
                tournament=tournament
            )

    return redirect('review_entries', tournament_id=tournament.pk)



@login_required
def review_entries(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams = tournament.teams.all()
    games = tournament.games.all()

    return render(request, 'review_entries.html', {
        'tournament': tournament,
        'teams': teams,
        'games': games
    })



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

def generate_round_robin_schedule(teams):
    if len(teams) % 2 != 0:
        teams.append(None)  # Add a dummy team for the bye
    
    n = len(teams)
    schedule = []

    for round_num in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            team1 = teams[i]
            team2 = teams[-i-1]
            if team1 and team2:
                round_matches.append((team1, team2))
        schedule.append(round_matches)
        teams.insert(1, teams.pop())  # Rotate teams to get new matchups
    
    return schedule

@login_required
def tournament_review(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    teams_with_numbers = tournament.teams.filter(team_number__isnull=False).exists()

    return render(request, 'tournament_review.html', {
        'tournament': tournament,
        'teams_with_numbers': teams_with_numbers
    })


@login_required
def reset_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    
    # Remove all games related to this tournament
    Game.objects.filter(tournament=tournament).delete()

    # Reset team numbers
    teams = tournament.teams.all()
    for team in teams:
        team.team_number = None
        team.save()
    
    return redirect('review_entries', tournament_id=tournament.pk)

class MatchupResultView(UpdateView):
    model = Matchup
    fields = ['winner']
    template_name = 'tournaments/matchup_result.html'
    
    def form_valid(self, form):
        matchup = form.instance
        team = self.request.user.team  # Assuming you have user-team association
        
        # Verify team is part of matchup
        if team not in [matchup.team_1, matchup.team_2]:
            messages.error(self.request, "You are not authorized to enter this result.")
            return redirect('matchup_detail', pk=matchup.pk)
        
        if not matchup.result_entered_by:
            # First team entering result
            matchup.result_entered_by = team
            messages.success(self.request, "Result entered. Waiting for confirmation.")
        else:
            # Second team confirming result
            if matchup.result_entered_by == team:
                messages.error(self.request, "Result already entered by your team.")
                return redirect('matchup_detail', pk=matchup.pk)
                
            if form.cleaned_data['winner'] == matchup.winner:
                matchup.result_confirmed = True
                messages.success(self.request, "Result confirmed!")
            else:
                matchup.conflict_flag = True
                messages.warning(self.request, "Result disputed. Admin will review.")
        
        matchup.save()
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('matchup_detail', kwargs={'pk': self.object.pk})

def tournament_schedule(request, tournament_id):
    """View for displaying the tournament schedule"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    rounds = tournament.rounds.all().prefetch_related('matchups')
    
    context = {
        'tournament': tournament,
        'rounds': rounds,
    }
    return render(request, 'tournaments/schedule.html', context)

class TeamDashboard(DetailView):
    model = Team
    template_name = 'tournaments/team_dashboard.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        tournament = team.tournament
        
        # Get current round
        current_round = Round.objects.filter(
            tournament=tournament,
            is_active=True
        ).first()

        # Get team's matchups for current round
        current_matchups = None
        if current_round:
            current_matchups = Matchup.objects.filter(
                round=current_round
            ).filter(
                Q(team_1=team) | Q(team_2=team)
            ).select_related('game', 'team_1', 'team_2')

        # Get upcoming matchups
        upcoming_matchups = Matchup.objects.filter(
            Q(team_1=team) | Q(team_2=team),
            round__start_time__gt=timezone.now()
        ).select_related('round', 'game', 'team_1', 'team_2')[:5]

        # Get recent notifications
        recent_notifications = Notification.objects.filter(
            team=team,
            read_at__isnull=True
        ).order_by('-created_at')[:5]

        context.update({
            'current_round': current_round,
            'current_matchups': current_matchups,
            'upcoming_matchups': upcoming_matchups,
            'notifications': recent_notifications,
        })
        return context

def team_qr_code(request, team_id):
    """Generate QR code for team access"""
    team = get_object_or_404(Team, id=team_id)
    
    # Generate QR code with team's access token
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    team_url = request.build_absolute_uri(
        reverse('team_access', args=[team.access_token])
    )
    qr.add_data(team_url)
    qr.make(fit=True)

    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    # Return image
    return HttpResponse(
        buffer.getvalue(),
        content_type='image/png'
    )

def team_access(request, access_token):
    """Handle team access via QR code"""
    team = get_object_or_404(Team, access_token=access_token)
    
    # Set session variable for team access
    request.session['team_id'] = team.id
    
    return redirect('team_dashboard', pk=team.id)

class WagerFormView(DetailView):
    model = Team
    template_name = 'tournaments/wager_form.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        games = Game.objects.filter(tournament=team.tournament)
        existing_wagers = {
            w.game_id: w.points 
            for w in Wager.objects.filter(team=team)
        }
        
        context['games'] = [
            {
                'game': game,
                'points': existing_wagers.get(game.id, 0)
            }
            for game in games
        ]
        return context
    
    def post(self, request, *args, **kwargs):
        team = self.get_object()
        games = Game.objects.filter(tournament=team.tournament)
        
        # Validate total points
        total_points = sum(
            int(request.POST.get(f'game_{game.id}', 0))
            for game in games
        )
        
        if total_points != 100:
            messages.error(request, 'Total points must equal 100')
            return self.get(request, *args, **kwargs)
        
        # Save wagers
        with transaction.atomic():
            Wager.objects.filter(team=team).delete()
            for game in games:
                points = int(request.POST.get(f'game_{game.id}', 0))
                if points > 0:
                    Wager.objects.create(
                        team=team,
                        game=game,
                        points=points
                    )
        
        messages.success(request, 'Wagers saved successfully')
        return redirect('team_dashboard', pk=team.id)

# Public views (no login required)
class TournamentStandingsView(ListView):
    model = TournamentStanding
    template_name = 'tournaments/standings.html'
    context_object_name = 'standings'

    def get_queryset(self):
        tournament_id = self.kwargs.get('tournament_id')
        return TournamentStanding.objects.filter(
            tournament_id=tournament_id
        ).select_related('team').order_by('-total_points', '-wager_points')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament_id = self.kwargs.get('tournament_id')
        context['tournament'] = Tournament.objects.get(id=tournament_id)
        return context

class NotificationListView(ListView):
    model = Notification
    template_name = 'tournaments/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            team_id=self.kwargs.get('team_id')
        ).select_related('related_matchup', 'related_round')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['team'] = get_object_or_404(Team, id=self.kwargs.get('team_id'))
        return context

def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    if request.method == 'POST':
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

class TeamDashboard(DetailView):
    model = Team
    template_name = 'tournaments/team_dashboard.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        tournament = team.tournament
        
        # Get current round
        current_round = Round.objects.filter(
            tournament=tournament,
            is_active=True
        ).first()

        # Get team's matchups for current round
        current_matchups = None
        if current_round:
            current_matchups = Matchup.objects.filter(
                round=current_round
            ).filter(
                Q(team_1=team) | Q(team_2=team)
            ).select_related('game', 'team_1', 'team_2')

        # Get upcoming matchups
        upcoming_matchups = Matchup.objects.filter(
            Q(team_1=team) | Q(team_2=team),
            round__start_time__gt=timezone.now()
        ).select_related('round', 'game', 'team_1', 'team_2')[:5]

        # Get recent notifications
        recent_notifications = Notification.objects.filter(
            team=team,
            read_at__isnull=True
        ).order_by('-created_at')[:5]

        context.update({
            'current_round': current_round,
            'current_matchups': current_matchups,
            'upcoming_matchups': upcoming_matchups,
            'notifications': recent_notifications,
        })
        return context

def team_qr_code(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    # Generate QR code for team access
    import qrcode
    import qrcode.image.svg
    from io import BytesIO

    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(
        f'/team/access/{team.access_token}/',
        image_factory=factory, 
        box_size=20
    )
    stream = BytesIO()
    img.save(stream)
    return HttpResponse(stream.getvalue(), content_type='image/svg+xml')

def team_access(request, access_token):
    team = get_object_or_404(Team, access_token=access_token)
    return redirect('team_dashboard', pk=team.id)

class WagerFormView(DetailView):
    model = Team
    template_name = 'tournaments/wager_form.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        games = Game.objects.filter(tournament=team.tournament)
        existing_wagers = {
            w.game_id: w.points 
            for w in Wager.objects.filter(team=team)
        }
        
        context['games'] = [
            {
                'game': game,
                'points': existing_wagers.get(game.id, 0)
            }
            for game in games
        ]
        return context
    
    def post(self, request, *args, **kwargs):
        team = self.get_object()
        games = Game.objects.filter(tournament=team.tournament)
        
        # Validate total points
        total_points = sum(
            int(request.POST.get(f'game_{game.id}', 0))
            for game in games
        )
        
        if total_points != 100:
            messages.error(request, 'Total points must equal 100')
            return self.get(request, *args, **kwargs)
        
        # Save wagers
        with transaction.atomic():
            Wager.objects.filter(team=team).delete()
            for game in games:
                points = int(request.POST.get(f'game_{game.id}', 0))
                if points > 0:
                    Wager.objects.create(
                        team=team,
                        game=game,
                        points=points
                    )
        
        messages.success(request, 'Wagers saved successfully')
        return redirect('team_dashboard', pk=team.id)

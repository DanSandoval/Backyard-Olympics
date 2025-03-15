from django import forms
from .models import Tournament, Team, Game, Round, Matchup, Wager, Notification

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'description']

class TeamForm(forms.ModelForm):
    members = forms.CharField(widget=forms.Textarea, help_text="Enter team member names, separated by commas")
    phone_number_1 = forms.CharField(max_length=20, required=False, help_text="Primary contact phone")
    phone_number_2 = forms.CharField(max_length=20, required=False, help_text="Secondary contact phone")
    email_1 = forms.EmailField(required=False, help_text="Primary contact email")
    email_2 = forms.EmailField(required=False, help_text="Secondary contact email")

    class Meta:
        model = Team
        fields = ['name', 'members', 'phone_number_1', 'phone_number_2', 'email_1', 'email_2']

class GameForm(forms.ModelForm):
    rules = forms.CharField(widget=forms.Textarea, required=False, help_text="Enter game rules (optional)")
    
    class Meta:
        model = Game
        fields = ['name', 'description', 'rules']

class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ['round_number', 'start_time', 'length_minutes', 'is_current']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class MatchupForm(forms.ModelForm):
    class Meta:
        model = Matchup
        fields = ['game', 'round', 'team1', 'team2']
        
class WagerForm(forms.ModelForm):
    class Meta:
        model = Wager
        fields = ['game', 'points']
        
    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        
    def clean_points(self):
        points = self.cleaned_data.get('points')
        if points < 0:
            raise forms.ValidationError("Points cannot be negative")
        return points
        
    def clean(self):
        cleaned_data = super().clean()
        if self.team:
            # Check total wager points for this team
            points = cleaned_data.get('points', 0)
            total_existing = Wager.objects.filter(team=self.team).exclude(
                pk=self.instance.pk if self.instance and self.instance.pk else None
            ).aggregate(total=models.Sum('points'))['total'] or 0
            
            if total_existing + points > 100:
                self.add_error('points', f"Total points exceed 100. Current total: {total_existing}, adding {points}.")
        return cleaned_data

class NotificationForm(forms.ModelForm):
    all_teams = forms.BooleanField(required=False, help_text="Send to all teams")
    
    class Meta:
        model = Notification
        fields = ['title', 'message', 'team']
        
    def clean(self):
        cleaned_data = super().clean()
        all_teams = cleaned_data.get('all_teams')
        team = cleaned_data.get('team')
        
        if all_teams and team:
            self.add_error('team', "Cannot select both a specific team and 'all teams'")
        elif not all_teams and not team:
            self.add_error('team', "Must select either a specific team or 'all teams'")
            
        return cleaned_data
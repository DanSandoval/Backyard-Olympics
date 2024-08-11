from django import forms
from .models import Tournament, Team, Game

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'description']

from django import forms
from .models import Team

class TeamForm(forms.ModelForm):
    members = forms.CharField(widget=forms.Textarea, help_text="Enter team member names, separated by commas")

    class Meta:
        model = Team
        fields = ['name', 'members']


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'description']

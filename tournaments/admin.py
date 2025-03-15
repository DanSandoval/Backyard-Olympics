from django.contrib import admin
from .models import Tournament, Team, Game, Round, Matchup, Wager, Notification

class TeamInline(admin.TabularInline):
    model = Team
    extra = 0
    fields = ['name', 'team_number', 'members']

class GameInline(admin.TabularInline):
    model = Game
    extra = 0
    fields = ['name', 'description']

class RoundInline(admin.TabularInline):
    model = Round
    extra = 0
    fields = ['round_number', 'start_time', 'length_minutes', 'is_current']

class WagerInline(admin.TabularInline):
    model = Wager
    extra = 0
    fields = ['game', 'points']

class MatchupInline(admin.TabularInline):
    model = Matchup
    extra = 0
    fields = ['game', 'team1', 'team2', 'result', 'conflict_flag']

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'team_count', 'game_count', 'round_count']
    search_fields = ['name', 'description']
    inlines = [TeamInline, GameInline, RoundInline]
    
    def team_count(self, obj):
        return obj.teams.count()
    
    def game_count(self, obj):
        return obj.games.count()
    
    def round_count(self, obj):
        return obj.rounds.count()
    
    team_count.short_description = 'Teams'
    game_count.short_description = 'Games'
    round_count.short_description = 'Rounds'

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'tournament', 'team_number', 'members_short', 'win_count']
    list_filter = ['tournament']
    search_fields = ['name', 'members']
    inlines = [WagerInline]
    
    def members_short(self, obj):
        if len(obj.members) > 50:
            return f"{obj.members[:50]}..."
        return obj.members
    
    def win_count(self, obj):
        return obj.get_wins()
    
    members_short.short_description = 'Members'
    win_count.short_description = 'Wins'

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'tournament', 'description_short']
    list_filter = ['tournament']
    search_fields = ['name', 'description']
    
    def description_short(self, obj):
        if obj.description and len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description or ""
    
    description_short.short_description = 'Description'

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'round_number', 'start_time', 'length_minutes', 'is_current']
    list_filter = ['tournament', 'is_current']
    search_fields = ['tournament__name']
    inlines = [MatchupInline]

@admin.register(Matchup)
class MatchupAdmin(admin.ModelAdmin):
    list_display = ['game', 'round', 'team1', 'team2', 'result', 'conflict_flag']
    list_filter = ['round__tournament', 'round', 'conflict_flag', 'result']
    search_fields = ['game__name', 'team1__name', 'team2__name']
    
    fieldsets = (
        (None, {
            'fields': ('game', 'round', 'team1', 'team2', 'result', 'is_bye')
        }),
        ('Conflict Management', {
            'fields': ('conflict_flag', 'team1_reported_win', 'team2_reported_win', 'conflict_notes')
        }),
    )

@admin.register(Wager)
class WagerAdmin(admin.ModelAdmin):
    list_display = ['team', 'game', 'points']
    list_filter = ['team__tournament', 'game']
    search_fields = ['team__name', 'game__name']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'tournament', 'team', 'created_at', 'is_read']
    list_filter = ['tournament', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'team__name']
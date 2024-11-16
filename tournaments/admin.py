from django.contrib import admin
from django.utils.html import format_html
from .models import Tournament, Team, Round, Game, Matchup, Wager

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'team_count', 'current_round']
    search_fields = ['name']

    def team_count(self, obj):
        return obj.teams.count()
    team_count.short_description = 'Number of Teams'

    def current_round(self, obj):
        active_round = obj.rounds.filter(is_active=True).first()
        return active_round.round_number if active_round else '-'
    current_round.short_description = 'Current Round'

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'round_number', 'start_time', 'end_time', 'is_active', 'is_completed']
    list_filter = ['tournament', 'is_active']
    search_fields = ['tournament__name']
    actions = ['activate_round', 'deactivate_round']

    def activate_round(self, request, queryset):
        # Deactivate all other rounds in the same tournament
        for round in queryset:
            Round.objects.filter(tournament=round.tournament).update(is_active=False)
            round.is_active = True
            round.save()
    activate_round.short_description = "Activate selected round"

    def deactivate_round(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_round.short_description = "Deactivate selected round"

@admin.register(Matchup)
class MatchupAdmin(admin.ModelAdmin):
    list_display = ['game', 'round', 'team_1', 'team_2', 'winner', 'status_badge', 'result_confirmed']
    list_filter = ['conflict_flag', 'result_confirmed', 'round', 'game']
    search_fields = ['team_1__name', 'team_2__name', 'game__name']
    readonly_fields = ['result_entered_by']
    actions = ['resolve_conflict', 'reset_matchup']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'game', 'round', 'team_1', 'team_2', 'winner', 'result_entered_by'
        )
    
    def status_badge(self, obj):
        if obj.conflict_flag:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">'
                'CONFLICT</span>'
            )
        elif obj.result_confirmed:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">'
                'CONFIRMED</span>'
            )
        elif obj.result_entered_by:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 8px; border-radius: 3px;">'
                'PENDING</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">'
            'NOT STARTED</span>'
        )
    status_badge.short_description = 'Status'

    def resolve_conflict(self, request, queryset):
        for matchup in queryset:
            matchup.conflict_flag = False
            matchup.result_confirmed = True
            matchup.save()
    resolve_conflict.short_description = "Resolve selected conflicts"

    def reset_matchup(self, request, queryset):
        queryset.update(
            winner=None,
            result_entered_by=None,
            result_confirmed=False,
            conflict_flag=False
        )
    reset_matchup.short_description = "Reset matchup results"

@admin.register(Wager)
class WagerAdmin(admin.ModelAdmin):
    list_display = ['team', 'game', 'points', 'total_team_points']
    list_filter = ['team', 'game']
    search_fields = ['team__name', 'game__name']

    def total_team_points(self, obj):
        total = Wager.objects.filter(team=obj.team).aggregate(
            total=models.Sum('points'))['total']
        return format_html(
            '<span style="color: {};">{}/100</span>',
            'red' if total > 100 else 'green',
            total
        )
    total_team_points.short_description = 'Total Team Points'

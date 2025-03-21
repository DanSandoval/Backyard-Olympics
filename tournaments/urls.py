from django.urls import path
from . import views

urlpatterns = [
    path('', views.choose_create_tournament, name='choose_create_tournament'),
    path('create/', views.create_tournament, name='create_tournament'),
    path('<int:pk>/', views.select_tournament, name='select_tournament'),
    path('add_teams/<int:tournament_id>/', views.add_teams, name='add_teams'),
    path('add_games/<int:tournament_id>/', views.add_games, name='add_games'),
    path('tournament_review/<int:tournament_id>/', views.tournament_review, name='tournament_review'),
    path('team_list/<int:tournament_id>/', views.team_list, name='team_list'),
    path('game_list/<int:tournament_id>/', views.game_list, name='game_list'),
    path('tournament_begins/<int:tournament_id>/', views.tournament_begins, name='tournament_begins'),
    path('review_entries/<int:tournament_id>/', views.review_entries, name='review_entries'),
    path('print_grids/<int:tournament_id>/', views.print_grids, name='print_grids'),
    path('input_results/<int:tournament_id>/', views.input_results, name='input_results'),
    path('finalize_tournament/<int:tournament_id>/', views.finalize_tournament, name='finalize_tournament'),
    path('generate_matchups/<int:tournament_id>/', views.generate_matchups, name='generate_matchups'),
    path('reset_tournament/<int:tournament_id>/', views.reset_tournament, name='reset_tournament'),
    
    # New URLs for enhanced functionality
    path('next_round/<int:tournament_id>/', views.next_round, name='next_round'),
    path('previous_round/<int:tournament_id>/', views.previous_round, name='previous_round'),
    path('manage_wagers/<int:tournament_id>/', views.manage_wagers, name='manage_wagers'),
    path('manage_wagers/<int:tournament_id>/<int:team_id>/', views.manage_wagers, name='manage_wagers'),
    path('conflict_resolution/<int:tournament_id>/', views.conflict_resolution, name='conflict_resolution'),
    path('report_result/<int:tournament_id>/<int:matchup_id>/', views.report_result, name='report_result'),
    path('create_notification/<int:tournament_id>/', views.create_notification, name='create_notification'),
    path('mark_notification_read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('tournament_standings/<int:tournament_id>/', views.tournament_standings, name='tournament_standings'),
]
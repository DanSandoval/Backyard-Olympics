from django.urls import path
from . import views

urlpatterns = [
    path('', views.tournament_list, name='tournament_list'),
    path('<int:pk>/', views.tournament_detail, name='tournament_detail'),
    path('<int:pk>/teams/', views.team_list, name='team_list'),
    path('<int:pk>/teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('<int:pk>/games/', views.game_list, name='game_list'),
    path('<int:pk>/games/<int:game_id>/', views.game_detail, name='game_detail'),
    path('create/', views.create_tournament, name='create_tournament'),
    path('<int:pk>/teams/create/', views.create_team, name='create_team'),
    path('<int:pk>/games/create/', views.create_game, name='create_game'),
]

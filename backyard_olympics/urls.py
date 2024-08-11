"""
URL configuration for backyard_olympics project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from tournaments import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', views.home, name='home'),
    path('choose_create_tournament/', views.choose_create_tournament, name='choose_create_tournament'),
    path('create_tournament/', views.create_tournament, name='create_tournament'),
    path('select_tournament/<int:pk>/', views.select_tournament, name='select_tournament'),
    path('add_teams/<int:tournament_id>/', views.add_teams, name='add_teams'),
    path('add_games/<int:tournament_id>/', views.add_games, name='add_games'),
    path('tournament_review/<int:tournament_id>/', views.tournament_review, name='tournament_review'),
    path('team_list/<int:tournament_id>/', views.team_list, name='team_list'),
    path('game_list/<int:tournament_id>/', views.game_list, name='game_list'),
    path('tournament_begins/<int:tournament_id>/', views.tournament_begins, name='tournament_begins'),
    path('review_entries/<int:tournament_id>/', views.review_entries, name='review_entries'),
    path('print_grids/<int:tournament_id>/', views.print_grids, name='print_grids'),
    path('input_results/<int:tournament_id>/', views.input_results, name='input_results'),
]

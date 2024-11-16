from django.urls import path
from . import views

# Public URLs
urlpatterns = [
    # Tournament Standings
    path('tournament/<int:tournament_id>/standings/', 
         views.TournamentStandingsView.as_view(), 
         name='tournament_standings'),
    
    # Team Dashboard and Access
    path('team/<int:pk>/', 
         views.TeamDashboard.as_view(), 
         name='team_dashboard'),
    path('team/<int:team_id>/qr/', 
         views.team_qr_code, 
         name='team_qr_code'),
    path('team/access/<uuid:access_token>/', 
         views.team_access, 
         name='team_access'),
    
    # Wagers
    path('team/<int:pk>/wagers/', 
         views.WagerFormView.as_view(), 
         name='wager_form'),
    
    # Notifications
    path('team/<int:team_id>/notifications/', 
         views.NotificationListView.as_view(), 
         name='team_notifications'),
    path('notifications/<int:notification_id>/mark-read/', 
         views.mark_notification_read, 
         name='mark_notification_read'),
]

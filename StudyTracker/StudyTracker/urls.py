from django.urls import path
from tracker import views

urlpatterns = [
    path('', views.index, name='index'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    
    # Новые пути для расписания
    path('schedule/', views.schedule_view, name='schedule'),
    path('schedule/sync/', views.sync_schedule_view, name='sync_schedule'),
    path('schedule/settings/', views.schedule_settings_view, name='schedule_settings'),
    path('api/schedule/today/', views.api_schedule_today, name='api_schedule_today'),
]

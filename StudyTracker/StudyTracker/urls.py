from django.contrib import admin
from django.urls import path
from tracker import views

urlpatterns = [
    path('', views.index, name='index'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
]

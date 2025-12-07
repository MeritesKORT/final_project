from django.shortcuts import render, get_object_or_404
from django.shortcuts import HttpResponse
from .models import Project

def index(request):
    """
    Главная страница — список опубликованных проектов.
    """
    projects = Project.objects.filter(is_published=True).order_by('-created_at')
    return render(request, 'tracker/index.html', {'projects': projects})


def project_detail(request, pk):
    """
    Страница деталей одного проекта.
    """
    project = get_object_or_404(Project, pk=pk, is_published=True)
    return render(request, 'tracker/project_detail.html', {'project': project})
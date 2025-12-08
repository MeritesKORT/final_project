from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Project, TelegramUser, UserCredentials, ParsedLesson
from .schedule_service import ScheduleService

# forms.py не существует, создаю простую форму тут
from django import forms

class TokenForm(forms.Form):
    auth_token = forms.CharField(
        label="Токен авторизации",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите токен'}),
        required=False
    )


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


@login_required
def schedule_view(request):
    """Страница расписания (веб-версия)"""
    try:
        user = TelegramUser.objects.first()
    except:
        user = None

    if not user:
        messages.warning(request, "Сначала настройте доступ через Telegram бота")
        return render(request, 'tracker/schedule.html', {
            'days': [],
            'user': None,
            'start_date': timezone.now().date()
        })

    # Создаем сервис
    service = ScheduleService(user)

    # Определяем период
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today.strftime('%Y-%m-%d'))

    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = today

    # Получаем расписание
    schedule = service.get_user_schedule(start_date, start_date + timedelta(days=6))

    # Группируем по дням
    schedule_by_date = {}
    for lesson in schedule:
        date_str = lesson.date.strftime('%Y-%m-%d')
        if date_str not in schedule_by_date:
            schedule_by_date[date_str] = []
        schedule_by_date[date_str].append(lesson)

    # Формируем дни недели
    days = []
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        date_str = day_date.strftime('%Y-%m-%d')
        lessons = schedule_by_date.get(date_str, [])

        days.append({
            'date': day_date,
            'lessons': lessons,
            'is_today': day_date == today,
            'weekday': day_date.strftime('%A'),
        })

    context = {
        'days': days,
        'start_date': start_date,
        'prev_week': start_date - timedelta(days=7),
        'next_week': start_date + timedelta(days=7),
        'user': user,
    }

    return render(request, 'tracker/schedule.html', context)


@login_required
def sync_schedule_view(request):
    """Синхронизировать расписание (веб-версия)"""
    # Получаем пользователя (для примера - первого)
    try:
        user = TelegramUser.objects.first()
    except TelegramUser.DoesNotExist:
        messages.error(request, "Пользователь не найден")
        return redirect('schedule')

    # Создаем сервис
    service = ScheduleService(user)

    # Синхронизируем
    result = service.sync_schedule(force=True)

    if result['success']:
        messages.success(
            request,
            f"Синхронизировано {result.get('total', 0)} уроков "
            f"(новых: {result.get('created', 0)}, обновлено: {result.get('updated', 0)})"
        )
    else:
        messages.error(request, f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    return redirect('schedule')


@login_required
def schedule_settings_view(request):
    """Настройки расписания"""
    user = TelegramUser.objects.first()  # Заглушка — лучше связать с request.user
    if not user:
        messages.error(request, "Пользователь не найден")
        return redirect('schedule')

    # Получаем или создаём объект UserCredentials
    credentials, created = UserCredentials.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = TokenForm(request.POST)
        if form.is_valid():
            credentials.auth_token = form.cleaned_data['auth_token']
            credentials.save()
            messages.success(request, "Настройки сохранены")
            return redirect('schedule_settings')
    else:
        form = TokenForm(initial={'auth_token': credentials.auth_token})

    context = {
        'form': form,
        'user': user,
        'token': credentials.auth_token,
    }

    return render(request, 'tracker/schedule_settings.html', context)


def api_schedule_today(request):
    """API: Расписание на сегодня (JSON)"""
    user = TelegramUser.objects.first()  # Заглушка — лучше связать с request.user
    if not user:
        return JsonResponse({'error': 'Пользователь не найден'}, status=404)

    # Используем ScheduleService вместо ScheduleParser
    service = ScheduleService(user)

    # Предполагаем, что в ScheduleService есть метод get_today_schedule()
    # Если его нет — нужно добавить в schedule_service.py
    schedule = service.get_today_schedule()
    today = timezone.now().date()

    lessons_data = []
    for lesson in schedule.get(today, []):
        lessons_data.append({
            'time': f"{lesson.started_at.strftime('%H:%M')} - {lesson.finished_at.strftime('%H:%M')}",
            'subject': lesson.subject.name,
            'teacher': lesson.teacher.name,
            'room': lesson.room.name,
            'is_remote': lesson.is_remote,
        })

    return JsonResponse({
        'date': today.strftime('%Y-%m-%d'),
        'lessons': lessons_data,
        'count': len(lessons_data),
    })
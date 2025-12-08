# tracker/admin.py
from django.contrib import admin
from .models import TelegramUser, ManualLesson, ManualHomework

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'notify_before_lesson', 'created_at')
    search_fields = ('telegram_id', 'username', 'first_name')
    list_filter = ('notify_homework', 'created_at')

@admin.register(ManualLesson)
class ManualLessonAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'get_day_of_week_display', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'subject')
    search_fields = ('subject', 'teacher', 'classroom')
    ordering = ('day_of_week', 'start_time')

@admin.register(ManualHomework)
class ManualHomeworkAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'task_preview', 'due_date', 'is_done')
    list_filter = ('is_done', 'subject', 'due_date')
    search_fields = ('subject', 'task')
    ordering = ('due_date',)
    
    def task_preview(self, obj):
        return obj.task[:50] + '...' if len(obj.task) > 50 else obj.task
    task_preview.short_description = 'Задание'
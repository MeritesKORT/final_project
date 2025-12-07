from django.contrib import admin
from .models import TelegramUser, Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'tech_stack', 'created_at', 'is_published')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'tech_stack')

admin.site.register(TelegramUser)
from django.db import models

# Модель для хранения пользователей Telegram
class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="ID Telegram")
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Имя пользователя")
    notify_daily = models.BooleanField(default=True, verbose_name="Присылать ежедневно")
    notify_time = models.TimeField(default="06:00", verbose_name="Время уведомления")

    def __str__(self):
        return f"@{self.username or self.telegram_id}"

# Модель проекта
class Project(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    tech_stack = models.CharField(max_length=200, verbose_name="Технологии", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")

    def __str__(self):
        return self.title
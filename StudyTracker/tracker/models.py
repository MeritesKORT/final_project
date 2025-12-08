from django.db import models
from django.utils import timezone
import base64
from cryptography.fernet import Fernet
from django.conf import settings
import os

# Генерируем ключ шифрования
def get_encryption_key():
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        key = Fernet.generate_key()
        os.environ['ENCRYPTION_KEY'] = key.decode()
    return key

class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Настройки
    notify_before_lesson = models.IntegerField(default=15, verbose_name="Уведомлять за (минут)")
    notify_homework = models.BooleanField(default=True, verbose_name="Уведомлять о домашке")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"@{self.username or self.telegram_id}"

class ManualLesson(models.Model):
    """Расписание, добавленное вручную"""
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='lessons')
    
    subject = models.CharField(max_length=200, verbose_name="Предмет")
    day_of_week = models.IntegerField(
        choices=[
            (0, 'Понедельник'), (1, 'Вторник'), (2, 'Среда'),
            (3, 'Четверг'), (4, 'Пятница'), (5, 'Суббота'), (6, 'Воскресенье')
        ],
        verbose_name="День недели"
    )
    start_time = models.TimeField(verbose_name="Начало")
    end_time = models.TimeField(verbose_name="Окончание")
    
    classroom = models.CharField(max_length=50, blank=True, verbose_name="Аудитория")
    teacher = models.CharField(max_length=100, blank=True, verbose_name="Преподаватель")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.user}: {self.subject} ({self.get_day_of_week_display()})"

class ManualHomework(models.Model):
    """Домашнее задание, добавленное вручную"""
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='homeworks')
    
    subject = models.CharField(max_length=200, verbose_name="Предмет")
    task = models.TextField(verbose_name="Задание")
    due_date = models.DateTimeField(verbose_name="Срок сдачи")
    
    is_done = models.BooleanField(default=False, verbose_name="Выполнено")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.subject}: {self.task[:50]}..."

class Project(models.Model):
    """Проект (для портфолио)"""
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    tech_stack = models.CharField(max_length=200, verbose_name="Технологии", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")

    def __str__(self):
        return self.title

class UserCredentials(models.Model):
    """Данные для входа пользователя (шифрованные)"""
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE, related_name='credentials')
    
    # Шифрованные данные
    encrypted_login = models.TextField("Логин (шифр)", blank=True)
    encrypted_password = models.TextField("Пароль (шифр)", blank=True)
    
    # Токен и его срок
    auth_token = models.TextField("Токен авторизации", blank=True)
    token_expires = models.DateTimeField("Истекает", null=True, blank=True)
    
    # Статус
    is_active = models.BooleanField("Активен", default=True)
    last_login = models.DateTimeField("Последний вход", null=True, blank=True)
    login_attempts = models.IntegerField("Попыток входа", default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Данные входа пользователя"
        verbose_name_plural = "Данные входа пользователей"
    
    def __str__(self):
        return f"Данные для {self.user}"
    
    def encrypt_data(self, data):
        """Зашифровать данные"""
        if not data:
            return ""
        fernet = Fernet(get_encryption_key())
        encrypted = fernet.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt_data(self, encrypted_data):
        """Расшифровать данные"""
        if not encrypted_data:
            return ""
        try:
            fernet = Fernet(get_encryption_key())
            decrypted = fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except:
            return ""
    
    @property
    def login(self):
        """Получить логин (расшифрованный)"""
        return self.decrypt_data(self.encrypted_login)
    
    @login.setter
    def login(self, value):
        """Установить логин (зашифрованный)"""
        self.encrypted_login = self.encrypt_data(value)
    
    @property
    def password(self):
        """Получить пароль (расшифрованный)"""
        return self.decrypt_data(self.encrypted_password)
    
    @password.setter
    def password(self, value):
        """Установить пароль (зашифрованный)"""
        self.encrypted_password = self.encrypt_data(value)
    
    def has_credentials(self):
        """Есть ли данные для входа?"""
        return bool(self.encrypted_login and self.encrypted_password)
    
    def is_token_valid(self):
        """Действителен ли токен?"""
        return bool(
            self.auth_token and 
            self.token_expires and 
            timezone.now() < self.token_expires
        )

class ParsedTeacher(models.Model):
    """Преподаватель из Top Academy"""
    name = models.CharField("ФИО преподавателя", max_length=200, unique=True)
    short_name = models.CharField("Короткое имя", max_length=100, blank=True)
    
    class Meta:
        verbose_name = "Преподаватель (парсинг)"
        verbose_name_plural = "Преподаватели (парсинг)"
    
    def __str__(self):
        return self.name


class ParsedSubject(models.Model):
    """Предмет из Top Academy"""
    name = models.CharField("Название предмета", max_length=200, unique=True)
    short_name = models.CharField("Сокращение", max_length=50, blank=True)
    
    class Meta:
        verbose_name = "Предмет (парсинг)"
        verbose_name_plural = "Предметы (парсинг)"
    
    def __str__(self):
        return self.name


class ParsedRoom(models.Model):
    """Аудитория из Top Academy"""
    name = models.CharField("Аудитория", max_length=100, unique=True)
    description = models.TextField("Описание", blank=True)
    
    class Meta:
        verbose_name = "Аудитория (парсинг)"
        verbose_name_plural = "Аудитории (парсинг)"
    
    def __str__(self):
        return self.name


class ParsedLesson(models.Model):
    """Урок, полученный через парсинг Top Academy"""
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='parsed_lessons')
    
    # Основные данные
    date = models.DateField("Дата")
    lesson_number = models.IntegerField("Номер урока")
    started_at = models.TimeField("Начало")
    finished_at = models.TimeField("Окончание")
    
    # Связи с другими моделями
    subject = models.ForeignKey(ParsedSubject, on_delete=models.PROTECT, verbose_name="Предмет")
    teacher = models.ForeignKey(ParsedTeacher, on_delete=models.PROTECT, verbose_name="Преподаватель")
    room = models.ForeignKey(ParsedRoom, on_delete=models.PROTECT, verbose_name="Аудитория")
    
    # Флаги
    is_cancelled = models.BooleanField("Отменен", default=False)
    is_remote = models.BooleanField("Дистант", default=False)
    
    # Системные поля
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    last_sync = models.DateTimeField("Последняя синхронизация", auto_now=True)
    
    class Meta:
        verbose_name = "Урок (парсинг)"
        verbose_name_plural = "Уроки (парсинг)"
        ordering = ['date', 'lesson_number']
        unique_together = ['user', 'date', 'lesson_number', 'subject']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['user', 'is_cancelled']),
        ]
    
    def __str__(self):
        return f"{self.date} - Урок {self.lesson_number}: {self.subject.name}"
    
    @property
    def duration_minutes(self):
        """Длительность урока в минутах"""
        from datetime import datetime
        start = datetime.combine(self.date, self.started_at)
        end = datetime.combine(self.date, self.finished_at)
        return (end - start).seconds // 60
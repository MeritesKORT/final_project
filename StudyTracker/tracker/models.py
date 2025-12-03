from django.db import models

class Project(models.Model):
    title = models.CharField(max_length=200, vorbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    tech_stack = models.CharField(max_length=200, verbose_name='Технология', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_published = models.BooleanField(default=True, verbose_name='Опубликовано')

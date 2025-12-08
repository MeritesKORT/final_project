# tracker/forms.py
from django import forms
from .models import UserAuthToken

class TokenForm(forms.ModelForm):
    class Meta:
        model = UserAuthToken
        fields = ['auth_token', 'top_login', 'auto_sync', 'sync_frequency']
        widgets = {
            'auth_token': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Вставьте токен из Authorization header...',
                'class': 'form-control'
            }),
            'top_login': forms.TextInput(attrs={
                'placeholder': 'Логин от Top Academy',
                'class': 'form-control'
            }),
            'sync_frequency': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 168
            }),
        }
        labels = {
            'auth_token': 'Токен авторизации',
            'top_login': 'Логин (опционально)',
            'auto_sync': 'Автоматическая синхронизация',
            'sync_frequency': 'Частота синхронизации (часов)',
        }
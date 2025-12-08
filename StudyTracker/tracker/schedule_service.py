# tracker/schedule_service.py
import requests
import json
from datetime import datetime, timedelta
from django.utils import timezone
from .models import TelegramUser, ParsedLesson, ParsedTeacher, ParsedSubject, ParsedRoom, UserCredentials

class ScheduleService:
    """Сервис для работы с расписанием в Django"""
    
    def __init__(self, user):
        self.user = user
    
    def fetch_schedule_from_api(self, auth_token, month_date=None):
        """Получить расписание с API Top Academy"""
        if not auth_token:
            return None
        
        if month_date is None:
            month_date = timezone.now().date()
        
        url = "https://magni.top-academy.ru/api/v2/schedule/operations/get-month"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru,en;q=0.9',
            'Authorization': f'Bearer {auth_token}',
            'Origin': 'https://journal.tipp-academy.ru',
            'Referer': 'https://journal.tipp-academy.ru/',
        }
        
        params = {'date_filter': month_date.strftime('%Y-%m-%d')}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def save_schedule_to_db(self, schedule_data):
        """Сохранить расписание в базу данных"""
        if not schedule_data:
            return {'success': False, 'error': 'Нет данных'}
        
        created_count = 0
        updated_count = 0
        
        for lesson_data in schedule_data:
            try:
                # Получаем или создаем связанные объекты
                teacher, _ = ParsedTeacher.objects.get_or_create(
                    name=lesson_data['teacher_name']
                )
                
                subject, _ = ParsedSubject.objects.get_or_create(
                    name=lesson_data['subject_name']
                )
                
                room, _ = ParsedRoom.objects.get_or_create(
                    name=lesson_data['room_name']
                )
                
                # Парсим даты
                lesson_date = datetime.strptime(lesson_data['date'], '%Y-%m-%d').date()
                started_at = datetime.strptime(lesson_data['started_at'], '%H:%M').time()
                finished_at = datetime.strptime(lesson_data['finished_at'], '%H:%M').time()
                
                # Определяем дистант
                is_remote = 'дистант' in lesson_data['room_name'].lower()
                
                # Создаем или обновляем урок
                lesson, created = ParsedLesson.objects.update_or_create(
                    user=self.user,
                    date=lesson_date,
                    lesson_number=lesson_data['lesson'],
                    subject=subject,
                    defaults={
                        'started_at': started_at,
                        'finished_at': finished_at,
                        'teacher': teacher,
                        'room': room,
                        'is_remote': is_remote,
                        'last_sync': timezone.now(),
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                print(f"Ошибка обработки урока: {e}")
                continue
        
        return {
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'total': len(schedule_data)
        }
    
    def sync_schedule(self, force=False):
        """Синхронизировать расписание для пользователя"""
        try:
            # Получаем токен пользователя
            credentials = UserCredentials.objects.get(user=self.user)
            
            if not credentials.auth_token:
                return {'success': False, 'error': 'Токен не найден'}
            
            # Получаем расписание с API
            schedule_data = self.fetch_schedule_from_api(credentials.auth_token)
            
            if not schedule_data:
                # Если токен устарел, пытаемся обновить
                if force:
                    from tracker.token_manager import UserTokenManager
                    manager = UserTokenManager(self.user)
                    new_token, error = manager.get_token(force_refresh=True)
                    
                    if new_token:
                        schedule_data = self.fetch_schedule_from_api(new_token)
                
                if not schedule_data:
                    return {'success': False, 'error': 'Не удалось получить расписание'}
            
            # Сохраняем в базу
            result = self.save_schedule_to_db(schedule_data)
            return result
            
        except UserCredentials.DoesNotExist:
            return {'success': False, 'error': 'Пользователь не настроил доступ'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_schedule(self, start_date=None, end_date=None):
        """Получить расписание пользователя из БД"""
        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        lessons = ParsedLesson.objects.filter(
            user=self.user,
            date__range=[start_date, end_date],
            is_cancelled=False
        ).select_related('subject', 'teacher', 'room')
        
        return lessons
    
    def get_today_schedule(self):
        """Получить расписание на сегодня"""
        today = timezone.now().date()
        return self.get_user_schedule(today, today)
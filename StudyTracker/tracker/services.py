import requests
import json
from datetime import datetime, timedelta
from django.utils import timezone
from .models import TelegramUser, ParsedLesson, ParsedTeacher, ParsedSubject, ParsedRoom, UserAuthToken
from collections import defaultdict

class ScheduleParser:
    """Парсер расписания Top Academy"""
    
    def __init__(self, user):
        self.user = user
        self.base_url = "https://magni.top-academy.ru/api/v2/schedule/operations/get-month"
        self.session = requests.Session()
    
    def _get_auth_token(self):
        """Получить токен авторизации для пользователя"""
        try:
            token_obj = UserAuthToken.objects.get(user=self.user)
            return token_obj.auth_token
        except UserAuthToken.DoesNotExist:
            return None
    
    def _get_headers(self):
        """Получить заголовки для запроса"""
        token = self._get_auth_token()
        if not token:
            raise ValueError("Токен авторизации не найден. Добавьте токен в настройках.")
        
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru,en;q=0.9',
            'Authorization': f'Bearer {token}',
            'Origin': 'https://journal.tipp-academy.ru',
            'Referer': 'https://journal.tipp-academy.ru/',
        }
    
    def fetch_schedule(self, month_date=None):
        """
        Получить расписание с API Top Academy
        
        Args:
            month_date (datetime.date): Дата месяца для получения расписания
        
        Returns:
            list: Список уроков в формате JSON или None при ошибке
        """
        if month_date is None:
            month_date = timezone.now().date()
        
        params = {'date_filter': month_date.strftime('%Y-%m-%d')}
        
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Логируем ошибку
                print(f"API Error {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return None
    
    def parse_and_save_schedule(self, schedule_data):
        """
        Разобрать JSON и сохранить в базу данных
        
        Args:
            schedule_data (list): Список уроков из API
        
        Returns:
            dict: Результат операции
        """
        if not schedule_data:
            return {'success': False, 'error': 'Нет данных для обработки'}
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for lesson_data in schedule_data:
            try:
                # 1. Получаем или создаем связанные объекты
                teacher, _ = ParsedTeacher.objects.get_or_create(
                    name=lesson_data['teacher_name']
                )
                
                subject, _ = ParsedSubject.objects.get_or_create(
                    name=lesson_data['subject_name']
                )
                
                room, _ = ParsedRoom.objects.get_or_create(
                    name=lesson_data['room_name']
                )
                
                # 2. Парсим даты и время
                lesson_date = datetime.strptime(lesson_data['date'], '%Y-%m-%d').date()
                started_at = datetime.strptime(lesson_data['started_at'], '%H:%M').time()
                finished_at = datetime.strptime(lesson_data['finished_at'], '%H:%M').time()
                
                # 3. Определяем, дистант ли урок
                is_remote = 'дистант' in lesson_data['room_name'].lower()
                
                # 4. Создаем или обновляем урок
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
                errors.append(f"Ошибка при обработке урока {lesson_data.get('date')}: {str(e)}")
        
        # Обновляем статус токена
        try:
            token_obj = UserAuthToken.objects.get(user=self.user)
            token_obj.last_sync_success = len(errors) == 0
            token_obj.last_sync_error = '; '.join(errors) if errors else ''
            token_obj.save()
        except:
            pass
        
        return {
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'total': len(schedule_data),
            'errors': errors,
        }
    
    def get_user_schedule(self, start_date=None, end_date=None):
        """
        Получить расписание пользователя из БД
        
        Args:
            start_date (datetime.date): Начальная дата
            end_date (datetime.date): Конечная дата
        
        Returns:
            dict: Расписание, сгруппированное по датам
        """
        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        lessons = ParsedLesson.objects.filter(
            user=self.user,
            date__range=[start_date, end_date],
            is_cancelled=False
        ).select_related('subject', 'teacher', 'room')
        
        # Группируем по датам
        schedule_by_date = defaultdict(list)
        for lesson in lessons.order_by('date', 'lesson_number'):
            schedule_by_date[lesson.date].append(lesson)
        
        return dict(schedule_by_date)
    
    def get_today_schedule(self):
        """Получить расписание на сегодня"""
        today = timezone.now().date()
        return self.get_user_schedule(today, today)
    
    def get_next_lesson(self):
        """Получить следующий урок"""
        now = timezone.now()
        today = now.date()
        current_time = now.time()
        
        # Ищем уроки на сегодня, которые еще не начались
        today_lessons = ParsedLesson.objects.filter(
            user=self.user,
            date=today,
            started_at__gte=current_time,
            is_cancelled=False
        ).order_by('started_at').first()
        
        if today_lessons:
            return today_lessons
        
        # Если сегодня больше нет уроков, ищем на завтра
        tomorrow = today + timedelta(days=1)
        tomorrow_lessons = ParsedLesson.objects.filter(
            user=self.user,
            date=tomorrow,
            is_cancelled=False
        ).order_by('started_at').first()
        
        return tomorrow_lessons
    
    def sync_schedule(self):
        """Полная синхронизация расписания"""
        # Получаем данные с API
        schedule_data = self.fetch_schedule()
        
        if schedule_data:
            # Сохраняем в БД
            result = self.parse_and_save_schedule(schedule_data)
            return result
        else:
            return {
                'success': False,
                'error': 'Не удалось получить данные с API'
            }
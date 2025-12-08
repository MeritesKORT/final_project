import requests
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ScheduleParserBot:
    """Парсер расписания"""
    
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self.base_url = "https://magni.top-academy.ru/api/v2/schedule/operations/get-month"
        self.session = requests.Session()
    
    def fetch_schedule(self, month_date=None):
        """Получить расписание с API"""
        if not self.auth_token:
            return None
        
        if month_date is None:
            month_date = datetime.now().date()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru,en;q=0.9',
            'Authorization': f'Bearer {self.auth_token}',
            'Origin': 'https://journal.tipp-academy.ru',
            'Referer': 'https://journal.tipp-academy.ru/',
        }
        
        params = {'date_filter': month_date.strftime('%Y-%m-%d')}
        
        try:
            response = self.session.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API ошибка {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None
    
    def format_schedule_for_today(self, schedule_data):
        """Форматировать расписание на сегодня"""
        if not schedule_data:
            return "📭 Расписание на сегодня не найдено"
        
        today = datetime.now().date().strftime('%Y-%m-%d')
        today_lessons = [l for l in schedule_data if l['date'] == today]
        
        if not today_lessons:
            return f"🎉 Сегодня ({today}) занятий нет!"
        
        today_lessons.sort(key=lambda x: x['lesson'])
        
        message = f"📅 РАСПИСАНИЕ НА СЕГОДНЯ ({today})\n\n"
        
        for i, lesson in enumerate(today_lessons, 1):
            message += f"{i}. {lesson['subject_name']}\n"
            message += f"   ⏰ {lesson['started_at']} - {lesson['finished_at']}\n"
            message += f"   👨‍🏫 {lesson['teacher_name']}\n"
            message += f"   🏫 {lesson['room_name']}\n"
            
            if 'дистант' in lesson['room_name'].lower():
                message += "   💻 Дистанционный урок\n"
            
            message += "\n"
        
        message += f"📊 Всего занятий: {len(today_lessons)}"
        return message
    
    def format_schedule_for_tomorrow(self, schedule_data):
        """Расписание на завтра"""
        if not schedule_data:
            return "📭 Расписание на завтра не найдено"
        
        tomorrow = (datetime.now() + timedelta(days=1)).date().strftime('%Y-%m-%d')
        tomorrow_lessons = [l for l in schedule_data if l['date'] == tomorrow]
        
        if not tomorrow_lessons:
            return f"🎉 Завтра ({tomorrow}) занятий нет!"
        
        tomorrow_lessons.sort(key=lambda x: x['lesson'])
        
        message = f"📅 РАСПИСАНИЕ НА ЗАВТРА ({tomorrow})\n\n"
        
        for i, lesson in enumerate(tomorrow_lessons, 1):
            message += f"{i}. {lesson['subject_name']}\n"
            message += f"   ⏰ {lesson['started_at']} - {lesson['finished_at']}\n"
            message += f"   👨‍🏫 {lesson['teacher_name']}\n"
            message += f"   🏫 {lesson['room_name']}\n\n"
        
        message += f"📊 Всего занятий: {len(tomorrow_lessons)}"
        return message
    
    def get_next_lesson(self, schedule_data):
        """Получить следующий урок"""
        if not schedule_data:
            return None
        
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        today = now.strftime('%Y-%m-%d')
        
        # Ищем уроки на сегодня
        today_lessons = [
            l for l in schedule_data 
            if l['date'] == today and l['started_at'] > current_time
        ]
        
        if today_lessons:
            today_lessons.sort(key=lambda x: x['started_at'])
            return today_lessons[0]
        
        # Ищем первый урок завтра
        tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow_lessons = [l for l in schedule_data if l['date'] == tomorrow]
        
        if tomorrow_lessons:
            tomorrow_lessons.sort(key=lambda x: x['lesson'])
            return tomorrow_lessons[0]
        
        return None

    def format_next_lesson(self, schedule_data):
        """Форматировать следующий урок"""
        next_lesson = self.get_next_lesson(schedule_data)
        
        if not next_lesson:
            return "📭 Следующих занятий не найдено"
        
        if next_lesson['date'] == datetime.now().strftime('%Y-%m-%d'):
            when = "сегодня"
        else:
            when = "завтра"
        
        message = f"⏭️ СЛЕДУЮЩЕЕ ЗАНЯТИЕ ({when})\n\n"
        message += f"📚 {next_lesson['subject_name']}\n"
        message += f"📅 {next_lesson['date']}\n"
        message += f"⏰ {next_lesson['started_at']} - {next_lesson['finished_at']}\n"
        message += f"👨‍🏫 {next_lesson['teacher_name']}\n"
        message += f"🏫 {next_lesson['room_name']}"
        
        return message
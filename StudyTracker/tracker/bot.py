import telebot
from django.conf import settings
from .models import TelegramUser, UserScheduleToken
from .schedule_parser import ScheduleParserBot
from dotenv import load_dotenv
import os
import sys
import django
import types
import datetime


# Загружаем переменные из .env
load_dotenv()

# Пробуем разные имена переменных
TOKEN = (
    os.getenv('BOT_TOKEN') or 
    os.getenv('TELEGRAM_BOT_TOKEN') or 
    os.getenv('TELEGRAM_TOKEN') or 
    os.getenv('BOT_API_TOKEN')
)

if not TOKEN:
    print("❌ ОШИБКА: Токен не найден!")
    sys.exit(1)

print(f"✅ Токен загружен: {TOKEN[:15]}...")
print("🤖 Запуск бота...")

# Настройка Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StudyTracker.settings')

try:
    django.setup()
    print("✅ Django настроен")
except Exception as e:
    print(f"❌ Ошибка Django: {e}")
    sys.exit(1)

# ИМПОРТ МОДЕЛЕЙ - ИСПРАВЛЕНО!
try:
    # Добавляем папку проекта в sys.path
    project_path = os.path.dirname(BASE_DIR)
    sys.path.append(project_path)
    
    from tracker.models import TelegramUser, ManualLesson, ManualHomework
    print("✅ Модели загружены")
except ImportError as e:
    print(f"❌ Ошибка импорта моделей: {e}")
    print(f"Текущий sys.path: {sys.path}")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
print("=" * 50)
print("🤖 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ!")
print("=" * 50)

# Вспомогательные функции
def get_weekday_name(weekday_index):
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    return days[weekday_index] if 0 <= weekday_index < 7 else "Неизвестный день"

# Обработчики сообщений
@bot.message_handler(commands=['start', 'help'])
def start(message):
    try:
        user, created = TelegramUser.objects.get_or_create(
            telegram_id=message.from_user.id,
            defaults={
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
            }
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📅 Сегодня", "📚 Задания")
        markup.add("➕ Добавить пару", "➕ Добавить домашку")
        markup.add("⚙️ Настройки", "❓ Помощь")
        
        if created:
            text = f"🎓 Добро пожаловать, {message.from_user.first_name}!"
        else:
            text = f"👋 С возвращением, {message.from_user.first_name}!"
        
        text += """

Я - твой помощник для учёбы!

*Что могу:*
• 📅 Показывать расписание
• 📚 Отслеживать задания
• ➕ Добавлять новые пары и домашки

Используй кнопки ниже!"""
        
        bot.send_message(message.chat.id, text, reply_markup=markup)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "📅 Сегодня")
def today(message):
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        today_date = datetime.now().date()
        weekday = today_date.weekday()
        day_name = get_weekday_name(weekday)
        
        lessons = ManualLesson.objects.filter(user=user, day_of_week=weekday).order_by('start_time')
        
        if lessons.exists():
            text = f"📅 *{day_name}*:\n\n"
            for i, lesson in enumerate(lessons, 1):
                text += f"{i}. *{lesson.start_time.strftime('%H:%M')}-{lesson.end_time.strftime('%H:%M')}*\n"
                text += f"   {lesson.subject}\n"
                if lesson.teacher:
                    text += f"   👨‍🏫 {lesson.teacher}\n"
                if lesson.classroom:
                    text += f"   🏫 {lesson.classroom}\n"
                text += "\n"
        else:
            text = f"🎉 *На {day_name} пар нет!*\n\nДобавь пары через '➕ Добавить пару'"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить пару на сегодня", callback_data=f"add_today_{weekday}"))
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        
    except TelegramUser.DoesNotExist:
        bot.send_message(message.chat.id, "Сначала нажми /start")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить пару")
def add_lesson_start(message):
    msg = bot.send_message(
        message.chat.id,
        "📝 *Добавление пары*\n\n"
        "Введите в формате:\n"
        "*День_недели Время Предмет*\n\n"
        "Пример:\n"
        "понедельник 09:00-10:30 Математика\n"
        "вторник 14:00-15:30 Физика",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_add_lesson)

def process_add_lesson(message):
    try:
        data = message.text.strip().split(' ', 2)
        if len(data) != 3:
            bot.send_message(message.chat.id, "❌ Неверный формат! Нужно: День Время Предмет")
            return
        
        day_str, time_str, subject = data
        
        # Дни недели
        days_map = {
            'понедельник': 0, 'вторник': 1, 'среда': 2,
            'четверг': 3, 'пятница': 4, 'суббота': 5, 'воскресенье': 6,
            'пн': 0, 'вт': 1, 'ср': 2, 'чт': 3, 'пт': 4, 'сб': 5, 'вс': 6
        }
        
        day = days_map.get(day_str.lower())
        if day is None:
            bot.send_message(message.chat.id, "❌ Неверный день недели! Используйте: понедельник, вторник и т.д.")
            return
        
        # Время
        if '-' not in time_str:
            bot.send_message(message.chat.id, "❌ Неверный формат времени! Используйте: 09:00-10:30")
            return
            
        start_str, end_str = time_str.split('-')
        try:
            start_time = datetime.strptime(start_str.strip(), '%H:%M').time()
            end_time = datetime.strptime(end_str.strip(), '%H:%M').time()
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат времени! Используйте ЧЧ:ММ, например: 09:00")
            return
        
        # Сохраняем
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        lesson = ManualLesson.objects.create(
            user=user,
            subject=subject,
            day_of_week=day,
            start_time=start_time,
            end_time=end_time
        )
        
        day_name = get_weekday_name(day)
        bot.send_message(
            message.chat.id,
            f"✅ *Пара добавлена!*\n\n"
            f"📅 *День:* {day_name}\n"
            f"🕐 *Время:* {time_str}\n"
            f"📚 *Предмет:* {subject}\n\n"
            f"Всего пар на {day_name}: {ManualLesson.objects.filter(user=user, day_of_week=day).count()}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "📚 Задания")
def show_homework(message):
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        now = datetime.now()
        
        # Активные задания
        active_hw = ManualHomework.objects.filter(
            user=user, 
            is_done=False,
            due_date__gt=now
        ).order_by('due_date')
        
        # Просроченные
        overdue_hw = ManualHomework.objects.filter(
            user=user,
            is_done=False,
            due_date__lt=now
        ).order_by('due_date')
        
        text = "📚 *Ваши задания*\n\n"
        
        if active_hw.exists():
            text += "*🔵 Активные:*\n"
            for hw in active_hw:
                days_left = (hw.due_date - now).days
                if days_left == 0:
                    deadline = f"Сегодня в {hw.due_date.strftime('%H:%M')}"
                    emoji = "⏰"
                elif days_left == 1:
                    deadline = f"Завтра в {hw.due_date.strftime('%H:%M')}"
                    emoji = "⚠️"
                elif days_left < 7:
                    deadline = f"Через {days_left} дней"
                    emoji = "📌"
                else:
                    deadline = hw.due_date.strftime("%d.%m.%Y")
                    emoji = "📅"
                
                text += f"{emoji} *{hw.subject}*\n"
                text += f"   {hw.task[:50]}...\n"
                text += f"   📅 {deadline}\n\n"
        
        if overdue_hw.exists():
            text += "\n*🔴 Просроченные:*\n"
            for hw in overdue_hw:
                text += f"❌ *{hw.subject}*\n"
                text += f"   {hw.task[:50]}...\n"
                text += f"   ⏰ Просрочено\n\n"
        
        if not active_hw.exists() and not overdue_hw.exists():
            text += "🎉 *Заданий нет!*\nМожно отдохнуть 😊"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить задание", callback_data="add_hw"))
        
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        
    except TelegramUser.DoesNotExist:
        bot.send_message(message.chat.id, "Сначала нажми /start")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить домашку")
def add_homework_start(message):
    msg = bot.send_message(
        message.chat.id,
        "📝 *Добавление задания*\n\n"
        "Введите в формате:\n"
        "*Предмет Задание Дедлайн*\n\n"
        "Пример:\n"
        "Математика Упражнения 1-5 15.12.2024 18:00\n"
        "Физика Лабораторная работа 20.12.2024 23:59",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_add_homework)

def process_add_homework(message):
    try:
        # Простой парсинг
        text = message.text.strip()
        
        # Пробуем найти дату в формате ДД.ММ.ГГГГ ЧЧ:ММ
        import re
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})', text)
        
        if not date_match:
            bot.send_message(
                message.chat.id,
                "❌ Не найден дедлайн в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Пример: 15.12.2024 18:00"
            )
            return
        
        due_str = date_match.group(1)
        due_date = datetime.strptime(due_str, '%d.%m.%Y %H:%M')
        
        # Выделяем предмет и задание
        subject_task = text.replace(due_str, '').strip()
        
        if len(subject_task) < 2:
            bot.send_message(message.chat.id, "❌ Слишком короткое описание!")
            return
        
        # Разделяем на предмет и задание (первые слова - предмет)
        parts = subject_task.split(' ', 1)
        if len(parts) == 2:
            subject, task = parts
        else:
            subject = parts[0]
            task = "Задание"
        
        # Сохраняем
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        hw = ManualHomework.objects.create(
            user=user,
            subject=subject,
            task=task,
            due_date=due_date
        )
        
        bot.send_message(
            message.chat.id,
            f"✅ *Задание добавлено!*\n\n"
            f"📚 *Предмет:* {subject}\n"
            f"📝 *Задание:* {task[:50]}...\n"
            f"📅 *Дедлайн:* {due_str}\n\n"
            f"Всего активных заданий: {ManualHomework.objects.filter(user=user, is_done=False).count()}",
            parse_mode='Markdown'
        )
        
    except ValueError as e:
        bot.send_message(message.chat.id, f"❌ Ошибка формата даты: {str(e)}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

@bot.message_handler(func=lambda m: m.text in ["⚙️ Настройки", "❓ Помощь"])
def help_settings(message):
    if message.text == "⚙️ Настройки":
        bot.send_message(
            message.chat.id,
            "⚙️ *Настройки*\n\n"
            "В разработке:\n"
            "• Уведомления о парах\n"
            "• Автопарсинг расписания\n"
            "• Экспорт в Google Calendar\n\n"
            "Пока используйте ручной ввод через кнопки!",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            message.chat.id,
            "❓ *Помощь*\n\n"
            "*Основные функции:*\n"
            "• 📅 Сегодня - расписание на сегодня\n"
            "• 📚 Задания - список домашки\n"
            "• ➕ Добавить пару - добавить занятие\n"
            "• ➕ Добавить домашку - добавить задание\n\n"
            "*Формат добавления пары:*\n"
            "понедельник 09:00-10:30 Математика\n\n"
            "*Формат добавления домашки:*\n"
            "Математика Упражнения 15.12.2024 18:00\n\n"
            "Есть вопросы? Пиши разработчику!",
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("add_today_"):
        day = int(call.data.split("_")[2])
        day_name = get_weekday_name(day)
        bot.answer_callback_query(call.id, f"Используйте '➕ Добавить пару' для {day_name}")
    elif call.data == "add_hw":
        bot.answer_callback_query(call.id, "Используйте кнопку '➕ Добавить домашку'")

if __name__ == "__main__":
    try:
        print("\n" + "=" * 50)
        print("📡 Запускаю бота...")
        print("Для остановки нажмите Ctrl+C")
        print("=" * 50 + "\n")
        
        bot.polling(none_stop=True, interval=0, timeout=60)
        
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


@bot.message_handler(commands=['set_token'])
def set_token(message):
    """Установить токен для парсинга"""
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=message.from_user.id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
        }
    )
    
    # Получаем токен из сообщения
    token_text = message.text.replace('/set_token', '').strip()
    
    if not token_text:
        bot.reply_to(message, 
            "❌ Пожалуйста, укажите токен после команды:\n"
            "/set_token ваш_токен_здесь\n\n"
            "*Как получить токен:*\n"
            "1. Откройте DevTools в браузере (F12)\n"
            "2. Перейдите на страницу расписания\n" 
            "3. Найдите запрос к get-month\n"
            "4. Скопируйте Authorization header\n"
            "5. Отправьте команду /set_token скопированный_токен")
        return
    
    # Сохраняем токен
    token_obj, created = UserScheduleToken.objects.get_or_create(user=user)
    token_obj.auth_token = token_text
    token_obj.save()
    
    bot.reply_to(message, "✅ Токен успешно сохранен!\nТеперь можете использовать команды расписания.")

@bot.message_handler(commands=['schedule_today'])
def schedule_today(message):
    """Расписание на сегодня"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала зарегистрируйтесь с помощью /start")
        return
    
    # Проверяем токен
    try:
        token_obj = UserScheduleToken.objects.get(user=user)
        if not token_obj.auth_token:
            bot.reply_to(message, 
                "❌ Токен не установлен. Используйте /set_token ваш_токен")
            return
    except UserScheduleToken.DoesNotExist:
        bot.reply_to(message, 
            "❌ Токен не установлен. Используйте /set_token ваш_токен")
        return
    
    # Парсим расписание
    parser = ScheduleParserBot(user)
    schedule_data = parser.fetch_schedule()
    
    if schedule_data is None:
        bot.reply_to(message, 
            "❌ Не удалось получить расписание.\n"
            "Возможно:\n"
            "1. Токен устарел\n"
            "2. Проблемы с интернетом\n"
            "3. Сервер недоступен")
        return
    
    # Форматируем и отправляем
    formatted = parser.format_schedule_for_today(schedule_data)
    bot.send_message(message.chat.id, formatted, parse_mode='Markdown')

@bot.message_handler(commands=['schedule_tomorrow'])
def schedule_tomorrow(message):
    """Расписание на завтра"""
    user = TelegramUser.objects.get(telegram_id=message.from_user.id)
    
    try:
        token_obj = UserScheduleToken.objects.get(user=user)
        if not token_obj.auth_token:
            bot.reply_to(message, "❌ Токен не установлен")
            return
    except:
        bot.reply_to(message, "❌ Токен не установлен")
        return
    
    parser = ScheduleParserBot(user)
    schedule_data = parser.fetch_schedule()
    
    if schedule_data:
        formatted = parser.format_schedule_for_tomorrow(schedule_data)
        bot.send_message(message.chat.id, formatted, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Не удалось получить расписание")

@bot.message_handler(commands=['schedule_week'])
def schedule_week(message):
    """Расписание на неделю"""
    user = TelegramUser.objects.get(telegram_id=message.from_user.id)
    
    try:
        token_obj = UserScheduleToken.objects.get(user=user)
        if not token_obj.auth_token:
            bot.reply_to(message, "❌ Токен не установлен")
            return
    except:
        bot.reply_to(message, "❌ Токен не установлен")
        return
    
    parser = ScheduleParserBot(user)
    schedule_data = parser.fetch_schedule()
    
    if schedule_data:
        formatted = parser.format_schedule_for_week(schedule_data)
        bot.send_message(message.chat.id, formatted, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Не удалось получить расписание")

@bot.message_handler(commands=['next_lesson'])
def next_lesson(message):
    """Следующий урок"""
    user = TelegramUser.objects.get(telegram_id=message.from_user.id)
    
    try:
        token_obj = UserScheduleToken.objects.get(user=user)
        if not token_obj.auth_token:
            bot.reply_to(message, "❌ Токен не установлен")
            return
    except:
        bot.reply_to(message, "❌ Токен не установлен")
        return
    
    parser = ScheduleParserBot(user)
    schedule_data = parser.fetch_schedule()
    
    if schedule_data:
        formatted = parser.format_next_lesson(schedule_data)
        bot.send_message(message.chat.id, formatted, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Не удалось получить расписание")

@bot.message_handler(commands=['schedule_help'])
def schedule_help(message):
    """Помощь по командам расписания"""
    help_text = """
    📚 *Команды расписания:*
    
    /set_token - Установить токен для доступа к расписанию
    /schedule_today - Расписание на сегодня
    /schedule_tomorrow - Расписание на завтра  
    /schedule_week - Расписание на неделю
    /next_lesson - Следующее занятие
    /schedule_help - Эта справка
    
    *Как получить токен:*
    1. Зайдите на journal.tipp-academy.ru
    2. Откройте DevTools (F12)
    3. Перейдите в Network
    4. Найдите запрос get-month
    5. Скопируйте Authorization header
    6. Отправьте /set_token ваш_токен
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# Меню с кнопками
@bot.message_handler(commands=['schedule_menu'])
def schedule_menu(message):
    """Меню расписания с кнопками"""
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn_today = telebot.types.KeyboardButton('📅 Сегодня')
    btn_tomorrow = telebot.types.KeyboardButton('⏭️ Завтра')
    btn_week = telebot.types.KeyboardButton('📆 Неделя')
    btn_next = telebot.types.KeyboardButton('⏰ Следующий урок')
    btn_token = telebot.types.KeyboardButton('🔑 Установить токен')
    btn_help = telebot.types.KeyboardButton('❓ Помощь')
    
    markup.add(btn_today, btn_tomorrow, btn_week, btn_next, btn_token, btn_help)
    
    bot.send_message(
        message.chat.id,
        "🎛️ *Меню расписания*\nВыберите действие:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# Обработка кнопок
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработка текстовых команд (кнопок)"""
    user_text = message.text.lower()
    
    user = TelegramUser.objects.get(telegram_id=message.from_user.id)
    
    if user_text == '📅 сегодня':
        schedule_today(message)
    elif user_text == '⏭️ завтра':
        schedule_tomorrow(message)
    elif user_text == '📆 неделя':
        schedule_week(message)
    elif user_text == '⏰ следующий урок':
        next_lesson(message)
    elif user_text == '🔑 установить токен':
        bot.reply_to(message, "Отправьте команду /set_token ваш_токен")
    elif user_text == '❓ помощь':
        schedule_help(message)
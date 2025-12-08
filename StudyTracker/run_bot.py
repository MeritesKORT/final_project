import os
import sys
import django
import telebot
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 1. Настраиваем пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# 2. Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StudyTracker.settings')
django.setup()

# 3. Загружаем .env
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 4. Получаем токен бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
    print("   Добавьте: TELEGRAM_BOT_TOKEN=ваш_токен_бота")
    exit(1)

print(f"✅ Токен бота получен: {BOT_TOKEN[:10]}...")

# 5. Импортируем модели и менеджер
from tracker.models import TelegramUser
from tracker.token_manager import UserTokenManager

# 6. Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Глобальный словарь менеджеров
user_managers = {}

def get_user_manager(telegram_user):
    """Получить менеджер для пользователя"""
    if telegram_user.id not in user_managers:
        user_managers[telegram_user.id] = UserTokenManager(telegram_user)
    return user_managers[telegram_user.id]

# ================== КОМАНДЫ БОТА ==================

@bot.message_handler(commands=['start', 'старт'])
def start(message):
    """Регистрация пользователя"""
    logger.info(f"/start от @{message.from_user.username}")
    
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=message.from_user.id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
        }
    )
    
    if created:
        reply = f"""
👋 Привет, {message.from_user.first_name}!

Я бот для расписания Top Academy 🎓

📅 Чтобы начать, введите свои данные:
• /login - ввести логин и пароль

✨ После этого сможете получать расписание!
"""
    else:
        reply = f"""
👋 С возвращением, {message.from_user.first_name}!

Ваши команды:
• /login - изменить данные входа
• /today - расписание на сегодня
• /status - проверить статус
• /help - справка
"""
    
    bot.reply_to(message, reply)

@bot.message_handler(commands=['help', 'помощь'])
def help_cmd(message):
    """Справка по командам"""
    help_text = """
📚 ДОСТУПНЫЕ КОМАНДЫ:

🔐 Авторизация:
/start - Начало работы
/login - Ввести логин и пароль
/status - Проверить статус
/logout - Удалить мои данные

📅 Расписание:
/today - Расписание на сегодня
/tomorrow - Расписание на завтра  
/next - Следующее занятие

ℹ️ Информация:
/help - Эта справка
/about - О боте

✨ Просто напишите "сегодня" чтобы получить расписание!
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['about', 'обо'])
def about(message):
    """Информация о боте"""
    about_text = """
🤖 БОТ РАСПИСАНИЯ TOP ACADEMY

Версия: 2.0
Разработчик: StudyTracker Project

🔒 Безопасность:
• Данные шифруются
• Токены обновляются автоматически
• Можно удалить данные в любой момент

📱 Функции:
• Автоматическое получение расписания
• Поддержка нескольких пользователей
• Безопасное хранение данных

💡 Используйте /login чтобы начать!
"""
    bot.reply_to(message, about_text)

@bot.message_handler(commands=['login', 'войти'])
def login_command(message):
    """Начать процесс входа"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала выполните /start")
        return
    
    login_instructions = """
🔑 ВХОД В TOP ACADEMY

Введите ваш ЛОГИН от journal.tipp-academy.ru:

📝 Пример: student123 или ваш.email@example.com
"""
    
    bot.reply_to(message, login_instructions)
    bot.register_next_step_handler(message, process_login_step1)

def process_login_step1(message):
    """Обработка логина"""
    login = message.text.strip()
    
    if not login:
        bot.reply_to(message, "❌ Логин не может быть пустым. /login")
        return
    
    bot.send_message(message.chat.id, f"✅ Логин: {login}\n\nТеперь введите ваш ПАРОЛЬ:")
    bot.register_next_step_handler(message, lambda m: process_login_step2(m, login))

def process_login_step2(message, login):
    """Обработка пароля"""
    password = message.text.strip()
    
    if not password:
        bot.reply_to(message, "❌ Пароль не может быть пустым. /login")
        return
    
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        manager = get_user_manager(user)
        
        success, msg = manager.set_credentials(login, password)
        
        if success:
            bot.send_message(message.chat.id, "🔄 Проверяю данные...")
            
            token, error = manager.get_token()
            
            if token:
                response = f"""
✅ ВХОД УСПЕШЕН!

Ваши данные сохранены.
Теперь можете использовать:

• /today - расписание на сегодня
• /tomorrow - расписание на завтра
• /next - следующее занятие

Удалить данные: /logout
"""
                bot.send_message(message.chat.id, response)
            else:
                bot.send_message(message.chat.id, 
                    f"❌ Ошибка: {error}\n\n"
                    f"Проверьте логин/пароль и попробуйте: /login")
        else:
            bot.send_message(message.chat.id, f"❌ Ошибка: {msg}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['status', 'статус'])
def status_command(message):
    """Показать статус пользователя"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        manager = get_user_manager(user)
        
        status = manager.get_status()
        
        user_info = f"""
👤 ВАШ ПРОФИЛЬ

Имя: {user.first_name}
Логин: @{user.username or 'не указан'}

📊 СТАТУС:
{status}

💡 Команды:
/login - изменить данные
/logout - удалить данные
/today - расписание
"""
        
        bot.reply_to(message, user_info)
        
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала /start")

@bot.message_handler(commands=['logout', 'выйти'])
def logout_command(message):
    """Удалить данные пользователя"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        manager = get_user_manager(user)
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_yes = telebot.types.KeyboardButton('✅ Да')
        btn_no = telebot.types.KeyboardButton('❌ Нет')
        markup.add(btn_yes, btn_no)
        
        bot.send_message(message.chat.id,
            "⚠️ УДАЛИТЬ ВАШИ ДАННЫЕ?\n\n"
            "Это действие нельзя отменить.",
            reply_markup=markup
        )
        
        bot.register_next_step_handler(message, confirm_logout, manager)
        
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала /start")

def confirm_logout(message, manager):
    """Подтверждение удаления"""
    choice = message.text.lower()
    
    markup = telebot.types.ReplyKeyboardRemove()
    
    if choice in ['да', 'yes', '✅ да']:
        success = manager.clear_credentials()
        
        if success:
            bot.send_message(message.chat.id,
                "✅ ДАННЫЕ УДАЛЕНЫ\n\n"
                "Все ваши данные удалены.\n"
                "Для входа снова: /login",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id,
                "❌ Ошибка удаления",
                reply_markup=markup
            )
    else:
        bot.send_message(message.chat.id,
            "❌ Отменено",
            reply_markup=markup
        )

@bot.message_handler(commands=['today', 'сегодня'])
def schedule_today(message):
    """Расписание на сегодня"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        manager = get_user_manager(user)
        
        token, error = manager.get_token()
        
        if not token:
            bot.reply_to(message, f"❌ {error or 'Ошибка получения токена'}")
            return
        
        from tracker.schedule_parser import ScheduleParserBot
        parser = ScheduleParserBot(token)
        schedule_data = parser.fetch_schedule()
        
        if schedule_data is None:
            bot.reply_to(message, 
                "❌ Не удалось получить расписание.\n"
                "Попробуйте:\n"
                "1. /status - проверить статус\n"
                "2. /login - обновить данные")
            return
        
        formatted = parser.format_schedule_for_today(schedule_data)
        bot.send_message(message.chat.id, formatted)
        
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала /start")

@bot.message_handler(commands=['tomorrow', 'завтра'])
def schedule_tomorrow(message):
    """Расписание на завтра"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        manager = get_user_manager(user)
        
        token, error = manager.get_token()
        
        if not token:
            bot.reply_to(message, "❌ Сначала выполните /login")
            return
        
        from tracker.schedule_parser import ScheduleParserBot
        parser = ScheduleParserBot(token)
        schedule_data = parser.fetch_schedule()
        
        if schedule_data:
            formatted = parser.format_schedule_for_tomorrow(schedule_data)
            bot.send_message(message.chat.id, formatted)
        else:
            bot.reply_to(message, "❌ Не удалось получить расписание")
            
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала /start")

@bot.message_handler(commands=['next', 'следующий'])
def next_lesson(message):
    """Следующий урок"""
    try:
        user = TelegramUser.objects.get(telegram_id=message.from_user.id)
        manager = get_user_manager(user)
        
        token, error = manager.get_token()
        
        if not token:
            bot.reply_to(message, "❌ Сначала /login")
            return
        
        from tracker.schedule_parser import ScheduleParserBot
        parser = ScheduleParserBot(token)
        schedule_data = parser.fetch_schedule()
        
        if schedule_data:
            formatted = parser.format_next_lesson(schedule_data)
            bot.send_message(message.chat.id, formatted)
        else:
            bot.reply_to(message, "❌ Не удалось получить расписание")
            
    except TelegramUser.DoesNotExist:
        bot.reply_to(message, "❌ Сначала /start")

# ============ ОБРАБОТКА ТЕКСТА ============

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработка всех текстовых сообщений"""
    user_text = message.text.lower().strip()
    
    if user_text in ['сегодня', 'расписание', 'пары сегодня']:
        schedule_today(message)
    elif user_text in ['завтра', 'расписание на завтра']:
        schedule_tomorrow(message)
    elif user_text in ['следующий урок', 'следующая пара']:
        next_lesson(message)
    elif user_text in ['помощь', 'команды']:
        help_cmd(message)
    elif user_text in ['статус', 'мой статус']:
        status_command(message)
    elif 'привет' in user_text:
        bot.reply_to(message, f"👋 Привет, {message.from_user.first_name}! Напиши 'сегодня' для расписания")
    else:
        bot.reply_to(message, 
            "🤔 Не понял. Используйте:\n"
            "• 'Сегодня' - расписание\n"
            "• /login - для входа\n"
            "• /help - все команды")

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")
    print("=" * 50)
    print("🤖 БОТ РАСПИСАНИЯ С ЛОГИНОМ/ПАРОЛЕМ")
    print("=" * 50)
    print("✅ Django настроен")
    print(f"✅ Токен бота: {BOT_TOKEN[:15]}...")
    print("✅ Бот запущен")
    print("=" * 50)
    print("📱 Отправьте /start в Telegram")
    print("=" * 50)
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        print(f"❌ Ошибка: {e}")
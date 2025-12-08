import os
from dotenv import load_dotenv

load_dotenv()

class AuthConfig:
    # Данные для входа (храним в .env файле)
    LOGIN_URL = "https://journal.tipp-academy.ru/auth/login"
    SCHEDULE_URL = "https://journal.tipp-academy.ru/schedule"
    
    # Данные пользователя (ЗАПОЛНИ В .env!)
    USERNAME = os.getenv('TOP_ACADEMY_USERNAME', '')
    PASSWORD = os.getenv('TOP_ACADEMY_PASSWORD', '')
    
    # Настройки Selenium
    HEADLESS = True  # False - показывать браузер, True - скрытый режим
    TIMEOUT = 30  # секунд
    DRIVER_WAIT = 10  # секунд ожидания элементов
    
    # Селекторы (могут меняться при обновлении сайта)
    SELECTORS = {
        'username_input': 'input[name="LoginForm[username]"]',
        'password_input': 'input[name="LoginForm[password]"]',
        'remember_checkbox': 'input[name="LoginForm[rememberMe]"]',
        'submit_button': 'button[type="submit"]',
        'login_form': 'form[action="/auth/login"]',
        
        # Для поиска токена в Network
        'api_requests': ['get-month', 'api/v2/schedule']
    }
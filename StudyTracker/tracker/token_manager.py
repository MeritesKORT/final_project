import logging
from datetime import timedelta
from django.utils import timezone
from .auth.playwright_auth import PlaywrightAuth
from .models import UserCredentials, TelegramUser

logger = logging.getLogger(__name__)

class UserTokenManager:
    """Менеджер токенов для пользователя"""
    
    def __init__(self, telegram_user):
        self.user = telegram_user
        self.credentials = None
        self.load_credentials()
    
    def load_credentials(self):
        """Загрузить данные пользователя"""
        try:
            self.credentials, created = UserCredentials.objects.get_or_create(user=self.user)
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return False
    
    def set_credentials(self, login, password):
        """Установить логин и пароль"""
        if not self.credentials:
            return False, "Ошибка загрузки данных"
        
        try:
            self.credentials.login = login
            self.credentials.password = password
            self.credentials.save()
            return True, "Данные сохранены"
        except Exception as e:
            return False, f"Ошибка: {e}"
    
    def get_token(self, force_refresh=False):
        """Получить токен для пользователя"""
        if not self.credentials or not self.credentials.has_credentials():
            return None, "Данные для входа не установлены. Используйте /login"
        
        # Если есть валидный токен и не форсируем обновление
        if not force_refresh and self.credentials.is_token_valid():
            return self.credentials.auth_token, None
        
        # Нужен новый токен
        logger.info(f"Получение токена для {self.user.username}")
        
        try:
            # Используем Selenium
            auth = PlaywrightAuth(
                login=self.credentials.login,
                password=self.credentials.password,
                headless=True
            )
            
            token, error = auth.get_auth_token()
            
            if token:
                # Сохраняем токен
                self.credentials.auth_token = token
                self.credentials.token_expires = timezone.now() + timedelta(hours=4)
                self.credentials.last_login = timezone.now()
                self.credentials.login_attempts = 0
                self.credentials.save()
                
                logger.info(f"✅ Токен получен")
                return token, None
            else:
                self.credentials.login_attempts += 1
                self.credentials.save()
                
                error_msg = error or "Неизвестная ошибка"
                logger.error(f"❌ Ошибка: {error_msg}")
                return None, error_msg
                
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None, str(e)
    
    def clear_credentials(self):
        """Очистить данные пользователя"""
        if self.credentials:
            self.credentials.encrypted_login = ""
            self.credentials.encrypted_password = ""
            self.credentials.auth_token = ""
            self.credentials.save()
            return True
        return False
    
    def get_status(self):
        """Получить статус пользователя"""
        if not self.credentials:
            return "❌ Данные не загружены"
        
        if not self.credentials.has_credentials():
            return "❌ Логин/пароль не установлены"
        
        if self.credentials.is_token_valid():
            expires_in = self.credentials.token_expires - timezone.now()
            hours = int(expires_in.total_seconds() // 3600)
            minutes = int((expires_in.total_seconds() % 3600) // 60)
            return f"✅ Токен активен ({hours}ч {minutes}м)"
        else:
            return "❌ Токен недействителен"
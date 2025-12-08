import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class SimpleSeleniumAuth:
    """Простая авторизация через Selenium"""
    
    def __init__(self, login, password, headless=True):
        self.login = login
        self.password = password
        self.headless = headless
        self.driver = None
        
        # URL (без пробелов!)
        self.login_url = "https://journal.top-academy.ru/ru/auth/login/index"
        self.schedule_url = "https://journal.top-academy.ru/ru/main/schedule/page/index"
        
        # Селекторы (обновлены!)
        self.selectors = {
    'username': 'input[name="LoginForm[login]"]',
    'password': 'input[name="LoginForm[password]"]',
    'submit': 'button[type="submit"]',
}
    
    def setup_driver(self):
        """Настроить драйвер Chrome"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # Основные опции
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Убираем признаки автоматизации
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Установка драйвера
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Маскируем WebDriver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Драйвер Chrome настроен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка настройки драйвера: {e}")
            return False
    
    def perform_login(self):
        """Выполнить вход"""
        try:
            logger.info(f"Вход для пользователя: {self.login[:3]}...")
            
            # Переходим на страницу логина
            self.driver.get(self.login_url)
            time.sleep(5)
            
            # Отладка: посмотреть HTML
            logger.info("HTML страницы:")
            logger.info(self.driver.page_source[:1500])
            
            # Ждём форму
            wait = WebDriverWait(self.driver, 20)
            
            # Вводим логин
            logger.info("Ищем поле логина...")
            username_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['username']))
            )
            logger.info("Поле логина найдено!")
            username_input.clear()
            username_input.send_keys(self.login)
            
            # Вводим пароль
            logger.info("Ищем поле пароля...")
            password_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors['password'])
            logger.info("Поле пароля найдено!")
            password_input.clear()
            password_input.send_keys(self.password)
            
            # Нажимаем кнопку входа
            logger.info("Ищем кнопку входа...")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, self.selectors['submit'])
            logger.info("Кнопка входа найдена!")
            logger.info(f"Текст кнопки: {submit_button.text}")
            logger.info(f"Кнопка кликабельна: {submit_button.is_enabled()}")
            
            # Прокручиваем к кнопке
            self.driver.execute_script("arguments[0].scrollIntoView();", submit_button)
            time.sleep(1)
            
            self.driver.execute_script("arguments[0].click();", submit_button)
            logger.info("Кнопка 'Вход' нажата!")
            
            # Ждём
            time.sleep(5)
            
            # Проверяем успешность входа
            current_url = self.driver.current_url
            logger.info(f"Текущий URL: {current_url}")
            
            if "auth/login" not in current_url:
                logger.info(f"✅ Успешный вход")
                return True, None
            else:
                logger.error("❌ Не удалось выйти из формы входа")
                
                # Проверим, есть ли сообщение об ошибке
                try:
                    error_msg = self.driver.find_element(By.CSS_SELECTOR, "div.alert-danger, .error-message, .help-block-error, .text-danger")
                    logger.error(f"Сообщение об ошибке: {error_msg.text}")
                    return False, error_msg.text
                except Exception as e:
                    logger.error(f"Не найдено сообщение об ошибке: {e}")
                    
                    # Проверим, есть ли капча
                    try:
                        captcha = self.driver.find_element(By.CSS_SELECTOR, "div.g-recaptcha, iframe[src*='recaptcha']")
                        logger.error("Обнаружена капча!")
                        return False, "Обнаружена капча — автоматический вход невозможен"
                    except:
                        pass
                    
                    return False, "Не удалось выйти из формы входа"
                    
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            return False, str(e)
    
    def get_auth_token(self):
        """Получить токен авторизации"""
        if not self.setup_driver():
            return None, "Не удалось настроить браузер"
        
        try:
            # 1. Логинимся
            login_success, error = self.perform_login()
            if not login_success:
                return None, error or "Ошибка входа"
            
            # 2. Переходим на страницу расписания
            self.driver.get(self.schedule_url)
            time.sleep(5)
            
            # 3. Получаем cookies
            cookies = self.driver.get_cookies()
            
            # 4. Пробуем выполнить JavaScript для получения токена
            token = self._extract_token_via_js()
            
            if token:
                logger.info(f"✅ Токен получен")
                return token, None
            else:
                # Пробуем через cookies
                session_cookie = self._get_session_from_cookies(cookies)
                if session_cookie:
                    return session_cookie, None
                else:
                    return None, "Не удалось получить токен"
                    
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
            return None, str(e)
        finally:
            self.cleanup()
    
    def _extract_token_via_js(self):
        """Попытаться извлечь токен через JavaScript"""
        try:
            # JavaScript который ищет токен
            js_scripts = [
                # Проверяем localStorage
                """
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    var value = localStorage.getItem(key);
                    if (value && value.includes('eyJ') && value.length > 100) {
                        return value;
                    }
                }
                return null;
                """,
                # Проверяем sessionStorage
                """
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    var value = sessionStorage.getItem(key);
                    if (value && value.includes('eyJ') && value.length > 100) {
                        return value;
                    }
                }
                return null;
                """,
                # Ищем в скриптах
                """
                var scripts = document.getElementsByTagName('script');
                for (var i = 0; i < scripts.length; i++) {
                    var content = scripts[i].textContent;
                    if (content.includes('Bearer ') || content.includes('eyJ')) {
                        var matches = content.match(/eyJ[a-zA-Z0-9._-]+/g);
                        if (matches && matches.length > 0) {
                            return matches[0];
                        }
                    }
                }
                return null;
                """
            ]
            
            for js in js_scripts:
                try:
                    result = self.driver.execute_script(js)
                    if result and 'eyJ' in str(result):
                        token_match = re.search(r'eyJ[a-zA-Z0-9._-]+', str(result))
                        if token_match:
                            token = token_match.group(0)
                            if len(token) > 100 and token.count('.') >= 2:
                                return token
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка JS извлечения: {e}")
            return None
    
    def _get_session_from_cookies(self, cookies):
        """Получить сессию из cookies"""
        try:
            for cookie in cookies:
                if any(keyword in cookie['name'].lower() for keyword in ['session', 'token', 'auth']):
                    if 'value' in cookie and cookie['value']:
                        return cookie['value']
            return None
        except:
            return None
    
    def cleanup(self):
        """Очистка"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

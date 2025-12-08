import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class SimpleSeleniumAuth:
    """Простая авторизация через Selenium для одного пользователя"""
    
    def __init__(self, login, password, headless=True):
        self.login = login
        self.password = password
        self.headless = headless
        self.driver = None
        
        # URL
        self.login_url = "https://journal.tipp-academy.ru/auth/login"
        self.schedule_url = "https://journal.tipp-academy.ru/schedule"
        
        # Селекторы (могут потребоваться настройки под ваш сайт)
        self.selectors = {
            'username': 'input[name="LoginForm[username]"]',
            'password': 'input[name="LoginForm[password]"]',
            'submit': 'button[type="submit"]',
            'login_form': 'form[action="/auth/login"]'
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
            logger.info(f"Вход для пользователя: {self.login}")
            
            # Переходим на страницу логина
            self.driver.get(self.login_url)
            time.sleep(3)
            
            # Ждём форму
            wait = WebDriverWait(self.driver, 20)
            
            # Вводим логин
            username_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['username']))
            )
            username_input.clear()
            username_input.send_keys(self.login)
            logger.info("Логин введён")
            
            # Вводим пароль
            password_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors['password'])
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("Пароль введён")
            
            # Нажимаем кнопку входа
            submit_button = self.driver.find_element(By.CSS_SELECTOR, self.selectors['submit'])
            submit_button.click()
            logger.info("Кнопка входа нажата")
            
            # Ждём (можно добавить проверку успешности)
            time.sleep(5)
            
            # Проверяем успешность входа
            current_url = self.driver.current_url
            if "auth/login" not in current_url:
                logger.info(f"✅ Успешный вход! URL: {current_url}")
                return True
            else:
                # Проверяем ошибки
                try:
                    error_div = self.driver.find_element(By.CSS_SELECTOR, ".help-block-error")
                    error_text = error_div.text
                    logger.error(f"❌ Ошибка входа: {error_text}")
                    return False, error_text
                except:
                    logger.error("❌ Неизвестная ошибка входа")
                    return False, "Неизвестная ошибка"
                    
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            # Делаем скриншот для отладки
            try:
                self.driver.save_screenshot(f"login_error_{self.login}.png")
            except:
                pass
            return False, str(e)
    
    def get_auth_token(self):
        """Получить токен авторизации"""
        if not self.setup_driver():
            return None, "Не удалось настроить браузер"
        
        try:
            # 1. Логинимся
            login_result = self.perform_login()
            if not login_result:
                return None, "Ошибка входа"
            
            # 2. Переходим на страницу расписания
            self.driver.get(self.schedule_url)
            time.sleep(5)  # Ждём загрузки JavaScript
            
            # 3. Получаем cookies (альтернативный способ)
            cookies = self.driver.get_cookies()
            
            # 4. Пробуем выполнить JavaScript для получения токена
            token = self._extract_token_via_js()
            
            if token:
                logger.info(f"✅ Токен получен для {self.login}")
                return token, None
            else:
                logger.warning(f"Токен не найден для {self.login}, пробуем через cookies")
                
                # Пробуем через cookies (если сайт использует cookie-based auth)
                session_cookie = self._get_session_from_cookies(cookies)
                if session_cookie:
                    return session_cookie, None
                else:
                    return None, "Не удалось получить токен авторизации"
                    
        finally:
            # Закрываем драйвер
            self.cleanup()
    
    def _extract_token_via_js(self):
        """Попытаться извлечь токен через JavaScript"""
        try:
            # JavaScript который ищет токен в различных местах
            js_scripts = [
                # Проверяем localStorage
                """
                var tokens = [];
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    var value = localStorage.getItem(key);
                    if (value && value.includes('eyJ') && value.length > 100) {
                        tokens.push({key: key, value: value.substring(0, 100) + '...'});
                    }
                }
                return JSON.stringify(tokens);
                """,
                # Проверяем sessionStorage
                """
                var tokens = [];
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    var value = sessionStorage.getItem(key);
                    if (value && value.includes('eyJ') && value.length > 100) {
                        tokens.push({key: key, value: value.substring(0, 100) + '...'});
                    }
                }
                return JSON.stringify(tokens);
                """,
                # Ищем в скриптах на странице
                """
                var scripts = document.getElementsByTagName('script');
                var foundTokens = [];
                for (var i = 0; i < scripts.length; i++) {
                    var content = scripts[i].textContent;
                    if (content.includes('Bearer ') || content.includes('eyJ')) {
                        // Ищем JWT токен
                        var matches = content.match(/eyJ[a-zA-Z0-9._-]+/g);
                        if (matches) {
                            foundTokens = foundTokens.concat(matches);
                        }
                    }
                }
                return foundTokens.length > 0 ? foundTokens[0] : null;
                """
            ]
            
            for js in js_scripts:
                try:
                    result = self.driver.execute_script(js)
                    if result and 'eyJ' in str(result):
                        # Извлекаем чистый токен
                        import re
                        token_match = re.search(r'eyJ[a-zA-Z0-9._-]+', str(result))
                        if token_match:
                            token = token_match.group(0)
                            # Проверяем что это похоже на JWT токен
                            if len(token) > 100 and token.count('.') >= 2:
                                return token
                except Exception as e:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка JS извлечения: {e}")
            return None
    
    def _get_session_from_cookies(self, cookies):
        """Получить сессию из cookies"""
        try:
            # Ищем session cookies
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
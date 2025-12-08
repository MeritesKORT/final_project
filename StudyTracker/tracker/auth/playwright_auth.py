from playwright.sync_api import sync_playwright
import time
import re

class PlaywrightAuth:
    """Получает Bearer токен через браузер без Selenium"""

    def __init__(self, login, password, headless=True):
        self.login = login
        self.password = password
        self.headless = headless
        self.login_url = "https://journal.top-academy.ru/ru/auth/login/index"

    def get_auth_token(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()

                # 1. Открываем страницу входа
                page.goto(self.login_url)

                # 2. Ввод логина и пароля
                page.fill("input[name='LoginForm[login]']", self.login)
                page.fill("input[name='LoginForm[password]']", self.password)

                # 3. Нажимаем кнопку "Войти"
                page.click("button[type='submit']")

                # ждем загрузки кабинета
                page.wait_for_load_state("networkidle")

                # 4. Идём в JS-переменные — токен хранится в localStorage
                token = page.evaluate("localStorage.getItem('auth_token')")

                browser.close()

                if not token:
                    return None, "Токен не найден (возможно, неверный логин или пароль)"

                return token, None

        except Exception as e:
            return None, str(e)

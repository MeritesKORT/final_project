import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StudyTracker.settings')
django.setup()

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from django.conf import settings
from tracker.models import TelegramUser
from tracker.utils import get_todays_schedule

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    user = message.from_user
    TelegramUser.objects.update_or_create(
        telegram_id=user.id,
        defaults={'username': user.username}
    )
    await message.answer(
        "✅ Привет! Я буду присылать тебе расписание.\n"
        "По умолчанию — каждый день в 06:00.\n"
        "Напиши /schedule — чтобы получить расписание сейчас.",
        parse_mode="Markdown"
    )

@dp.message(Command("schedule"))
async def schedule(message: Message):
    text = get_todays_schedule()
    await message.answer(text, parse_mode="Markdown")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
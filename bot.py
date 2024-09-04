import logging
import asyncio
import os

import django
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, CommandObject
from aiogram.filters import Command
from asgiref.sync import sync_to_async


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from telegram_miniapp.models import User

API_TOKEN = '7526172076:AAGh7ubgHqMAKw3sEcVQI6eLtxq1tNWupqQ'
MINI_APP_URL = 'https://t.me/Gehdhhenebjsjdn_bot/Cryptoner_Test'  # Замените на URL вашего Mini App
BOT_URL = 'https://t.me/Gehdhhenebjsjdn_bot'

# Установите логирование
logging.basicConfig(level=logging.INFO)

# Создайте объекты бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart(deep_link=True))
async def send_welcome(message: types.Message, command: CommandObject):
    ref_id = command.args
    if str(ref_id) == str(message.chat.id):
        ref_id = None

    user, created = await sync_to_async(User.objects.get_or_create)(
        user_id=message.chat.id,
        defaults={
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'username': message.from_user.username,
            'ref_id': ref_id
        }
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Открыть Mini App', url=MINI_APP_URL)],
        [InlineKeyboardButton(text='Пригласить друга', callback_data='invite')]
    ])

    if ref_id is not None:
        try:
            await bot.send_message(int(ref_id), f"Отлично. По твоей ссылке зарегистрировался (-лась) {message.from_user.full_name} @{message.from_user.username}")
        except:
            pass

    await message.answer("Привет! Нажмите кнопку ниже, чтобы открыть наш Mini App", reply_markup=keyboard)


@dp.callback_query(F.data == 'invite')
async def invite_friends(callback_query: types.CallbackQuery):
    await callback_query.message.answer(f"Твоя ссылка для приглашения: {BOT_URL}?start={callback_query.message.chat.id}")


async def main():

    logging.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    # Запуск основного цикла событий
    asyncio.run(main())


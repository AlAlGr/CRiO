import logging
import asyncio
import os

import django
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, CommandObject
from aiogram.filters import Command
from asgiref.sync import sync_to_async
from django.utils import timezone


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


async def check_and_notify_users():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Открыть Mini App', url=MINI_APP_URL)]
        ])

    while True:
        users = await sync_to_async(list)(User.objects.all())  # Получаем всех пользователей из БД
        now = timezone.now()  # Текущее время

        for user in users:
            if user.last_collected:
                time_elapsed = (now - user.last_collected).total_seconds()  # Время, прошедшее с последнего сбора

                if time_elapsed >= 8 * 60 * 60:  # 8 часов в секундах
                    try:
                        # Отправляем сообщение пользователю
                        await bot.send_message(user.user_id, "Пора собрать монеты!", reply_markup=keyboard)

                    except Exception as e:
                        # Обработка других исключений
                        print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

        await asyncio.sleep(60)  # Проверять каждые 60 секунд

@dp.message(CommandStart(deep_link=True))
async def start_deep_link(message: types.Message, command: CommandObject):
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

@dp.message(CommandStart())
async def start_deep_link(message: types.Message):
    user, created = await sync_to_async(User.objects.get_or_create)(
        user_id=message.chat.id,
        defaults={
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'username': message.from_user.username,
            'ref_id': None
        }
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Открыть Mini App', url=MINI_APP_URL)],
        [InlineKeyboardButton(text='Пригласить друга', callback_data='invite')]
    ])

    await message.answer("Привет! Нажмите кнопку ниже, чтобы открыть наш Mini App", reply_markup=keyboard)

@dp.callback_query(F.data == 'invite')
async def invite_friends(callback_query: types.CallbackQuery):
    await callback_query.message.answer(f"Твоя ссылка для приглашения: {BOT_URL}?start={callback_query.message.chat.id}")

async def on_startup(dispatcher: Dispatcher):
    asyncio.create_task(check_and_notify_users())

async def main():
    logging.info("Starting bot...")
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == '__main__':
    # Запуск основного цикла событий
    asyncio.run(main())


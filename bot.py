import logging
import asyncio
import os
import time

import django
import pytonconnect
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, CommandObject
from aiogram.filters import Command
from aiogram.utils.web_app import safe_parse_webapp_init_data
from aiohttp.web_request import Request
from aiohttp.web_response import json_response
from asgiref.sync import sync_to_async
from django.utils import timezone
from pytonconnect import TonConnect
from pytoniq_core import Address

from telegram_miniapp.connector import get_connector
from telegram_miniapp.messages import get_comment_message

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
        [InlineKeyboardButton(text='Собрать CRiO', url=MINI_APP_URL)]
        ])

    while True:
        users = await sync_to_async(list)(User.objects.all())  # Получаем всех пользователей из БД
        now = timezone.now()  # Текущее время

        for user in users:
            if user.last_collected:
                time_elapsed = (now - user.last_collected).total_seconds()  # Время, прошедшее с последнего сбора

                if 8 * 60 * 60 <= time_elapsed <= (8 * 60 * 60) + 100 or (8 * 60 * 60) * 2 <= time_elapsed <= ((8 * 60 * 60) * 2) + 100:  # 8 часов в секундах
                    try:
                        # Отправляем сообщение пользователю
                        await bot.send_message(user.user_id, "Забери CRiO Token зайди в Booster", reply_markup=keyboard)

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
            await bot.send_message(int(ref_id), f"Отлично. По твоей ссылке зарегистрировался (-лась) {message.from_user.full_name}")
        except:
            pass

    await message.answer("Привет! Нажмите кнопку ниже, и начнется автоматический фарминг CRiO TOKEN. Бот вам отправит сообщение через 8 часов , чтоб вы забрали свои токены .", reply_markup=keyboard)

@dp.message(CommandStart())
async def start(message: types.Message):
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

    await message.answer("Привет! Нажмите кнопку ниже, и начнется автоматический фарминг CRiO TOKEN. Бот вам отправит сообщение через 8 часов , чтоб вы забрали свои токены .", reply_markup=keyboard)

@dp.callback_query(F.data == 'invite')
async def invite_friends(callback_query: types.CallbackQuery):
    await callback_query.message.answer(f"Твоя ссылка для приглашения: {BOT_URL}?start={callback_query.message.chat.id}")


async def command_wallet(chat_id: int):
    connector = get_connector(chat_id)
    connected = await connector.restore_connection()

    mk_b = InlineKeyboardBuilder()
    if connected:
        # mk_b.button(text='Send Transaction', callback_data='send_tr')
        # mk_b.button(text='Disconnect', callback_data='disconnect')
        pass
    else:
        wallets_list = TonConnect.get_wallets()
        count = 0
        for wallet in wallets_list:

            if count < 2:
                mk_b.button(text=wallet['name'], callback_data=f'connect:{wallet["name"]}')
            else:
                break

            count += 1
        mk_b.adjust(1, )
        await bot.send_message(chat_id, text='Выбери кошелёк для подключения', reply_markup=mk_b.as_markup())


async def connect_wallet(message: types.Message, wallet_name: str):
    connector = get_connector(message.chat.id)

    wallets_list = connector.get_wallets()
    wallet = None

    for w in wallets_list:
        if w['name'] == wallet_name:
            wallet = w

    if wallet is None:
        raise Exception(f'Unknown wallet: {wallet_name}')

    generated_url = await connector.connect(wallet)

    mk_b = InlineKeyboardBuilder()
    mk_b.button(text='Connect', url=generated_url)

    await message.answer(text='Подключи кошелёк', reply_markup=mk_b.as_markup())

    mk_b = InlineKeyboardBuilder()
    mk_b.button(text="Открыть Mini App", url=MINI_APP_URL)

    for _ in range(1, 180):
        await asyncio.sleep(1)
        if connector.connected:
            if connector.account.address:
                wallet_address = connector.account.address
                wallet_address = Address(wallet_address).to_str(is_bounceable=False)
                await message.answer(f'Ты подключил кошелёк с адресом:\n{wallet_address}', reply_markup=mk_b.as_markup())
            return

    await message.answer(f'Timeout error!', reply_markup=mk_b.as_markup())


@dp.callback_query(lambda call: True)
async def main_callback_handler(call: types.CallbackQuery):
    await call.answer()
    message = call.message
    data = call.data
    if data == "wallet":
        await command_wallet(message.chat.id)
    elif data == "send_tr":
        await send_transaction(message)
    elif data == 'disconnect':
        await disconnect_wallet(message)
    else:
        data = data.split(':')
        if data[0] == 'connect':
            await connect_wallet(message, data[1])


@dp.message(Command('transaction'))
async def send_transaction(message: types.Message):
    connector = get_connector(message.chat.id)
    connected = await connector.restore_connection()
    if not connected:
        await message.answer('Connect wallet first!')
        return

    transaction = {
        'valid_until': int(time.time() + 3600),
        'messages': [
            get_comment_message(
                destination_address='0:0000000000000000000000000000000000000000000000000000000000000000',
                amount=int(0.01 * 10 ** 9),
                comment='hello world!'
            )
        ]
    }

    await message.answer(text='Approve transaction in your wallet app!')
    try:
        await asyncio.wait_for(connector.send_transaction(
            transaction=transaction
        ), 300)
    except asyncio.TimeoutError:
        await message.answer(text='Timeout error!')
    except pytonconnect.exceptions.UserRejectsError:
        await message.answer(text='You rejected the transaction!')
    except Exception as e:
        await message.answer(text=f'Unknown error: {e}')


async def disconnect_wallet(message: types.Message):
    connector = get_connector(message.chat.id)
    await connector.restore_connection()
    await connector.disconnect()
    await message.answer('You have been successfully disconnected!')


async def on_startup(dispatcher: Dispatcher):
    asyncio.create_task(check_and_notify_users())

async def main():
    logging.info("Starting bot...")
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == '__main__':
    # Запуск основного цикла событий
    asyncio.run(main())


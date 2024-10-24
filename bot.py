import asyncio
import imghdr
import logging
import os
import time

import django
import pytonconnect
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.deep_linking import create_start_link
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.state import StateFilter
from aiogram.types.menu_button_commands import MenuButtonCommands, MenuButtonType, MenuButton
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from pytonconnect import TonConnect
from pytoniq_core import Address
from PIL import Image


from telegram_miniapp.connector import get_connector
from telegram_miniapp.messages import get_comment_message

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from telegram_miniapp.models import User, Club

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
        [InlineKeyboardButton(text='Собрать DGEM', url=MINI_APP_URL)]
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
                        await bot.send_message(user.user_id, "Забери DGEM Token зайди в Booster", reply_markup=keyboard)

                    except Exception as e:
                        # Обработка других исключений
                        print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

        await asyncio.sleep(60)  # Проверять каждые 60 секунд

@sync_to_async
def update_user_points(user_id: int, points_to_add: int):
    with transaction.atomic():  # Используем транзакцию для гарантии сохранности данных
        user = User.objects.get(user_id=user_id)
        user.points += points_to_add
        user.save()


@dp.message(CommandStart(deep_link=True))
async def start_deep_link(message: types.Message, command: CommandObject):
    if command.args and command.args.startswith("club_"):
        club_id = int(command.args.split("_")[1])

        user = await sync_to_async(User.objects.get)(user_id=message.from_user.id)
        club = await sync_to_async(Club.objects.get)(id=club_id)

        # Присваиваем пользователю club_id
        user.club_id = club.id
        user.points_per_hour = user.points_per_hour + int(user.points_per_hour * 0.025)
        await sync_to_async(user.save)()

        # Увеличиваем количество участников клуба
        club.count_members += 1
        await sync_to_async(club.save)()

        await message.answer(f"Вы присоединились к клубу {club.name}!")
    else:
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
        if ref_id is not None:
            is_premium = message.from_user.is_premium

            if is_premium:
                await update_user_points(user_id=int(ref_id), points_to_add=15000)
            else:
                await update_user_points(user_id=int(ref_id), points_to_add=10000)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Открыть Mini App', url=MINI_APP_URL)],
            [InlineKeyboardButton(text='Пригласить друга', callback_data='invite')]
        ])

        if ref_id is not None:
            try:
                await bot.send_message(int(ref_id), f"Отлично. По твоей ссылке зарегистрировался (-лась) {message.from_user.full_name}")
            except:
                pass

        await message.answer("Привет! Нажмите кнопку ниже, и начнется автоматический фарминг DGEM TOKEN. Бот вам отправит сообщение через 8 часов , чтоб вы забрали свои токены .", reply_markup=keyboard)

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

    await message.answer("Привет! Нажмите кнопку ниже, и начнется автоматический фарминг DGEM TOKEN. Бот вам отправит сообщение через 8 часов , чтоб вы забрали свои токены .", reply_markup=keyboard)


class CreateSquadState(StatesGroup):
    awaiting_club_name = State()
    awaiting_club_photo = State()

# Команда для создания клуба
@dp.message(Command(commands="create_squad"))
async def create_squad_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Проверяем, создавал ли пользователь уже клуб по полю creator_id
    club = await sync_to_async(Club.objects.filter)(creator_id=user_id)
    club = await sync_to_async(club.first)()

    if club:
        deep_link = await create_start_link(bot=message.bot, payload=f"club_{club.id}")
        await message.answer(
            f"Ваш сквад:\n"
            f"Название: {club.name}\n"
            f"Количество участников: {club.count_members}\n"
            f"Ссылка для пришлашения: {deep_link}"
        )
    else:
        # Если клуб не создан, начинаем создание
        await message.answer("Введите название вашего сквада:")
        await state.set_state(CreateSquadState.awaiting_club_name)

# Шаг 1: Получаем название клуба
@dp.message(StateFilter(CreateSquadState.awaiting_club_name))
async def get_club_name(message: types.Message, state: FSMContext):
    await state.update_data(club_name=message.text)
    await message.answer("Отправьте фото для сквада (размер не более 1024x1024, тип JPG):")
    await state.set_state(CreateSquadState.awaiting_club_photo)

# Шаг 2: Получаем и проверяем фото
@dp.message(F.photo, StateFilter(CreateSquadState.awaiting_club_photo))
async def get_club_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]  # Получаем самую большую версию изображения

    # Получаем объект файла
    file_info = await message.bot.get_file(photo.file_id)

    # Путь для сохранения файла
    photo_path = f"telegram_miniapp/static/images/club_photo_{message.from_user.id}.jpg"

    # Скачиваем файл
    await message.bot.download_file(file_info.file_path, destination=photo_path)

    if imghdr.what(photo_path) != 'jpeg':
        await message.answer("Пожалуйста, отправьте изображение в формате JPG.")
        os.remove(photo_path)  # Удаляем некорректный файл
        return

    img = Image.open(photo_path)
    if img.width > 1024 or img.height > 1024:
        await message.answer("Размер изображения слишком большой. Пожалуйста, отправьте фото размером до 1024x1024.")
        os.remove(photo_path)  # Удаляем некорректный файл
        return

    # Сохраняем фото в постоянное место
    final_photo_path = f"telegram_miniapp/static/images/club_photo_{message.from_user.id}.jpg"
    os.rename(photo_path, final_photo_path)

    # Обновляем состояние
    await state.update_data(photo_path=final_photo_path)

    # Переходим к созданию клуба
    await create_club(message, state)

# Окончание создания клуба и отправка реферальной ссылки
async def create_club(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()

    club_name = data['club_name']
    photo_path = data['photo_path']


    # Создаем запись в БД
    club = await sync_to_async(Club.objects.create)(
        name=club_name,
        creator_id=user_id,
        count_members=1
    )

    club = await sync_to_async(Club.objects.filter)(creator_id=user_id)
    club = await sync_to_async(club.first)()

    user = await sync_to_async(User.objects.get)(user_id=user_id)
    user.points_per_hour = user.points_per_hour + int(user.points_per_hour * 0.025)
    user.club_id = club.id
    await sync_to_async(user.save)()

    # Создаем реферальную ссылку для клуба
    deep_link = await create_start_link(bot=message.bot, payload=f"club_{club.id}")

    # Отправляем пользователю сообщение с реферальной ссылкой
    await message.answer(f"Сквад '{club_name}' создан! Вот ваша ссылка для приглашения в сквад: {deep_link}")

    # Завершаем состояние FSM
    await state.clear()


@dp.callback_query(F.data == 'invite')
async def invite_friends(callback_query: types.CallbackQuery):
    await callback_query.message.answer(f"Твоя ссылка для приглашения: {BOT_URL}?start={callback_query.message.chat.id}")


async def command_wallet(chat_id: int):
    mk_b = InlineKeyboardBuilder()

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
            break


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

async def start_bot():
    # commands = [
    #     types.BotCommand(command="start", description="Перезапустить бота"),
    # ]
    #
    # await bot.set_my_commands(commands)

    logging.info("Starting bot...")
    dp.startup.register(on_startup)
    await dp.start_polling(bot, skip_updates=True)


# if __name__ == '__main__':
#     # Запуск основного цикла событий
#     asyncio.run(main())


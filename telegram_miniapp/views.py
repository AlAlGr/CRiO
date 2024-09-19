import asyncio
import json
import threading

from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from pytoniq_core import Address

from .connector import get_connector
from telegram_miniapp.tc_storage import TcStorage
from .models import User, Task, Wallet, Character, Improvement, Booster
from bot import BOT_URL, command_wallet, connect_wallet


def get_or_create_user(data: dict) -> User:
    """
    Получает или создает пользователя на основе данных, полученных из Telegram Mini App.
    """
    user, created = User.objects.update_or_create(
        user_id=data['id'],
        defaults={
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'username': data.get('username', ''),
            'avatar_url': data.get('photo_url', '')
        }
    )
    return user

@csrf_exempt  # Отключаем CSRF защиту для примера, используйте это с осторожностью
def save_user(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)

        user_id = data.get('user_id')
        first_name = data.get('first_name')
        last_name = data.get('last_name', '')
        username = data.get('username', '')
        ref_id = data.get('ref_id', '')
        avatar_url = data.get('avatar_url', '')

        if not user_id:
            return JsonResponse({'success': False, 'error': 'User ID is required'}, status=400)

        # Сохраняем данные о пользователе
        user, created = User.objects.get_or_create(
            user_id=user_id,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'avatar_url': avatar_url,
                'ref_id': ref_id
            }
        )

        if not created:
            # Обновляем информацию о существующем пользователе
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.save()

        # Возвращаем успешный ответ
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def home2_view(request: HttpRequest) -> HttpResponse:
    """
    Страница, отображающая имя пользователя, его очки и список персонажей.
    """

    def convert_seconds_to_time(seconds: int):
        hours = seconds // 3600  # Получаем количество полных часов
        minutes = (seconds % 3600) // 60  # Остаток от деления на 3600 преобразуем в минуты

        # Форматируем строку с ведущими нулями для часов и минут
        return f"{hours:02}h {minutes:02}m"

    if request.method == 'GET':
        user_id = int(request.GET.get('user_id'))
        user = User.objects.get(user_id=user_id)
        character = Character.objects.get(id=user.character_id)

        now = timezone.now()
        time_elapsed = (now - user.last_collected).total_seconds()
        if time_elapsed > 28800.0:
            time_elapsed = 28800.0

        time_left_sec = 28800 - int(time_elapsed)  # 8 часов - сколько прошло уже
        time_left_hours = convert_seconds_to_time(time_left_sec)

        # Максимум очков за 8 часов
        max_points = user.points_per_hour * 8

        # Текущий прогресс в заполнении
        progress = min(time_elapsed / 28800, 1) * 100  # 28800 секунд = 8 часов

        current_points = round((max_points * progress) / 100, 4)

        total_steps = max_points / 0.1  # 0.1 - шаг

        delay = 28800 / total_steps * 1000  # milliseconds

        context = {
            'user': user,
            'character': character,
            'progress': progress,
            'max_points': max_points,
            'current_points': current_points - 0.1,
            'delay': delay,
            'time_left_hours': time_left_hours
        }

        return render(request, 'home2.html', context)

def auth_view(request: HttpRequest) -> HttpResponse:
    """
    Аутентификация пользователя.
    """
    if request.method == 'GET':

        context = {}
        return render(request, 'home.html', context)


def frens_view(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        ref_users = User.objects.filter(ref_id=user_id)

    context = {
        'ref_users': ref_users,
        'count_ref_users': len(ref_users),
        'total_earn': len(ref_users) * 0.001,
        'share_link': f'{BOT_URL}?start={user_id}'
    }

    return render(request, 'frens.html', context)


def buy_character_view(request):
    user_id = request.GET.get('user_id')
    user = User.objects.get(user_id=user_id)

    characters = Character.objects.all()

    next_character_id = user.character_id + 1

    if request.method == 'POST':
        character_id = int(request.POST.get('character_id'))
        character = Character.objects.get(id=character_id)

        if user.buy_character(character):
            return redirect(f'/home2/?user_id={user_id}')

    context = {
        'user': user,
        'characters': characters,
        "next_character_id": next_character_id
    }

    return render(request, 'buy_character.html', context)

def buy_boosters_view(request):
    user_id = request.GET.get('user_id')
    user = User.objects.get(user_id=user_id)

    boosters = Booster.objects.all()

    next_booster_id = user.booster_id + 1

    if request.method == 'POST':
        booster_id = int(request.POST.get('booster_id'))
        booster = Booster.objects.get(id=booster_id)

        if user.buy_boosters(booster):
            return redirect(f'/home2/?user_id={user_id}')

    context = {
        'user': user,
        'boosters': boosters,
        "next_booster_id": next_booster_id
    }

    return render(request, 'buy_boosters.html', context)


def collect_points_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        character_id = data.get('character_id')

        user = get_object_or_404(User, user_id=user_id)
        character = get_object_or_404(Character, id=character_id)

        # Собираем очки
        points = user.points_per_hour * 8

        # Добавляем очки пользователю
        user.points += points
        user.last_collected = timezone.now()
        user.save()

        return JsonResponse({'success': True, 'points': user.points})
    return JsonResponse({'success': False}, status=400)


def wallet_view(request: HttpRequest) -> HttpResponse:
    """
    Синхронная страница привязки TON-кошелька.
    """
    user_id = int(request.GET.get('user_id'))
    wallet_address = "00000000000000000000000000000000000000000"
    connected = False

    connector = get_connector(user_id)
    connected = async_to_sync(connector.restore_connection)()

    if connected:
        wallet_address = connector.account.address
        wallet_address = Address(wallet_address).to_str(is_bounceable=False)
        connected = True

    context = {
        'connected': connected,
        'wallet_address': f"{wallet_address[:8]} ...",
        'bot_url': BOT_URL,
        'user_id': user_id
    }

    return render(request, 'wallet.html', context)

def disconnect_wallet_view(request) -> JsonResponse:
    if request.method == "POST":
        data = json.loads(request.body)
        chat_id = data.get('user_id')
        connector = get_connector(chat_id)
        asyncio.run(connector.restore_connection())
        asyncio.run(connector.disconnect())

        with open(f"wallet_storage/storage_{chat_id}.json", "w") as file:
            json.dump({}, file, ensure_ascii=False, indent=4)

        return JsonResponse({'success': True, 'chat_id': chat_id})
    return JsonResponse({'success': False}, status=400)


async def run_wallet_tasks(chat_id):
    await command_wallet(chat_id)


def redirect_to_bot_wallet(request) -> JsonResponse:
    if request.method == "POST":
        data = json.loads(request.body)
        chat_id = data.get('user_id')

        async_to_sync(run_wallet_tasks)(chat_id)

        return JsonResponse({'success': True, 'chat_id': chat_id})
    return JsonResponse({'success': False}, status=400)


def is_admin(user: User) -> bool:
    """
    Проверка, является ли пользователь администратором.
    """
    return user.is_staff  # Встроенное поле Django для проверки, является ли пользователь админом


@user_passes_test(is_admin)
def tasks_view(request: HttpRequest) -> HttpResponse:
    """
    Страница с заданиями. Администратор может добавлять новые задания.
    """
    user = get_object_or_404(User, user_id=request.GET.get('id'))
    tasks = Task.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now(), is_active=True)

    if request.method == 'POST' and user.is_staff:
        # Логика добавления нового задания администратором
        Task.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            icon=request.FILES.get('icon'),
            image=request.FILES.get('image'),
            reward=request.POST.get('reward'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            is_active=True
        )
        return redirect('tasks')

    context = {
        'user': user,
        'tasks': tasks
    }
    return render(request, 'tasks.html', context)


# def buy_character_view(request, character_id):
#     user = request.user
#     character = get_object_or_404(Character, id=character_id)
#
#     if request.method == 'POST':
#         if user.buy_character(character):
#             return redirect('home')
#         else:
#             return render(request, 'telegram_miniapp/error.html',
#                           {'message': 'Недостаточно очков для покупки персонажа.'})
#
#     return render(request, 'telegram_miniapp/buy_character.html', {'character': character})


def buy_improvement_view(request, improvement_id):
    user = request.user
    improvement = get_object_or_404(Improvement, id=improvement_id)

    if request.method == 'POST':
        if user.buy_improvement(improvement):
            return redirect('home')
        else:
            return render(request, 'telegram_miniapp/error.html',
                          {'message': 'Недостаточно очков для покупки улучшения.'})

    return render(request, 'telegram_miniapp/buy_improvement.html', {'improvement': improvement})

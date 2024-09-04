import json

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt

from .models import User, Task, Wallet, Character, Improvement


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
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        user = User.objects.get(user_id=user_id)
        character = get_object_or_404(Character, id=user.character_id)

        now = timezone.now()
        time_elapsed = (now - user.last_collected).total_seconds()
        if time_elapsed > 28800.0:
            time_elapsed = 28800.0

        # Максимум очков за 8 часов
        max_points = character.points_per_hour * 8

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
            'current_points': current_points,
            'delay': delay
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
    user = request.user
    referrals = User.objects.filter(referred_by=user)

    if request.method == 'POST':
        points_to_add = referrals.aggregate(Sum('daily_points'))['daily_points__sum'] * 0.10
        user.points += points_to_add
        user.save()
        return redirect('frens')

    return render(request, 'telegram_miniapp/frens.html', {'referrals': referrals})


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


def collect_points_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_id = data.get('user_id')
        character_id = data.get('character_id')

        user = get_object_or_404(User, user_id=user_id)
        character = get_object_or_404(Character, id=character_id)

        # Собираем очки
        points = character.points_per_hour * 8

        # Добавляем очки пользователю
        user.points += points
        user.last_collected = timezone.now()
        user.save()

        return JsonResponse({'success': True, 'points': user.points})
    return JsonResponse({'success': False}, status=400)


def wallet_view(request: HttpRequest) -> HttpResponse:
    """
    Страница привязки TON-кошелька.
    """
    user = get_object_or_404(User, user_id=request.GET.get('id'))

    if request.method == 'POST':
        wallet_address = request.POST.get('wallet_address')
        if wallet_address:
            Wallet.objects.update_or_create(user=user, defaults={'wallet_address': wallet_address})

    context = {
        'user': user,
        'wallet': user.wallet if hasattr(user, 'wallet') else None
    }
    return render(request, 'wallet.html', context)


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

from django.contrib import admin
from .models import User, Task, Character, Wallet, Booster, Club, Task

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Класс для управления моделью пользователя в админке.
    """
    list_display = ('user_id', 'first_name', 'last_name', 'username', 'points', 'created_at')
    search_fields = ('user_id', 'first_name', 'last_name', 'username')
    list_filter = ('created_at',)

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    """
    Класс для управления моделью персонажа в админке.
    """
    list_display = ('name', 'cost', 'points_per_hour')

@admin.register(Booster)
class BoosterAdmin(admin.ModelAdmin):
    """
    Класс для управления моделью улучшения в админке.
    """
    list_display = ('name', 'cost', 'points_per_hour')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """
    Класс для управления моделью кошелька в админке.
    """
    list_display = ('user_id', 'wallet_address')

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator_id', 'count_members')  # Какие поля отображать в списке
    search_fields = ('name',)  # Поля для поиска
    list_filter = ('creator_id',)  # Добавление фильтров по полям
    ordering = ('name',)  # Сортировка по имени клуба

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'reward')  # Поля для отображения в админке

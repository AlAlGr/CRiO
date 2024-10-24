from django.db import models
from django.utils import timezone

class Improvement(models.Model):
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    increase_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Процент увеличения

    def __str__(self):
        return self.name

class User(models.Model):
    user_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    last_collected = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    ref_id = models.BigIntegerField(blank=True, null=True)
    character_id = models.BigIntegerField(default=1)
    booster_id = models.BigIntegerField(default=0)
    club_id = models.BigIntegerField(null=True)

    points = models.PositiveIntegerField(default=0)
    points_per_hour = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    ton_wallet = models.CharField(max_length=255, blank=True, null=True)
    daily_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (@{self.username})"

    def collect_all_points(self) -> int:
        """
        Собирает все очки, заработанные пользователем от его персонажей.
        Возвращает общее количество собранных очков.
        """
        total_points = sum(character.collect_points() for character in self.characters.all())
        self.points += total_points
        self.last_collected = timezone.now()  # Обновляем время последнего сбора очков
        self.save()
        return total_points

    def can_buy_character(self, character) -> bool:
        return self.points >= character.cost and character.id == self.character_id + 1

    def can_buy_boosters(self, boosters) -> bool:
        return self.points >= boosters.cost

    def buy_character(self, character) -> bool:
        if self.can_buy_character(character):
            self.points -= character.cost
            self.character_id = character.id
            self.points_per_hour += character.points_per_hour
            self.save()
            return True
        return False

    def buy_boosters(self, boosters) -> bool:
        if self.can_buy_boosters(boosters):
            self.points -= boosters.cost
            self.booster_id = boosters.id
            self.points_per_hour += boosters.points_per_hour
            self.save()
            return True
        return False

class Club(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1024)
    creator_id = models.BigIntegerField(null=True)
    count_members = models.BigIntegerField(default=1)

class Character(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    points_per_hour = models.IntegerField()
    last_collected = models.DateTimeField(default=timezone.now)

    improvements = models.ManyToManyField('Improvement', blank=True)
    last_progress_update = models.DateTimeField(default=timezone.now)

    def calculate_points_per_hour(self) -> int:
        base_points = self.points_per_hour
        total_points = base_points
        for improvement in self.improvements.all():
            total_points += base_points * (improvement.increase_percentage / 100)
        return int(total_points)

    def collect_points(self) -> int:
        now = timezone.now()
        hours_elapsed = (now - self.last_collected).total_seconds() // 3600
        points = int(hours_elapsed * self.points_per_hour)
        if hours_elapsed > 8:
            points = self.points_per_hour * 8
        self.last_collected = now
        self.save()
        return points

class Booster(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    points_per_hour = models.IntegerField()

    def calculate_points_per_hour(self) -> int:
        base_points = self.points_per_hour
        total_points = base_points
        for improvement in self.improvements.all():
            total_points += base_points * (improvement.increase_percentage / 100)
        return int(total_points)

    def collect_points(self) -> int:
        now = timezone.now()
        hours_elapsed = (now - self.last_collected).total_seconds() // 3600
        points = int(hours_elapsed * self.points_per_hour)
        if hours_elapsed > 8:
            points = self.points_per_hour * 8
        self.last_collected = now
        self.save()
        return points

class UserBooster(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boosters')  # Связь с пользователем
    booster = models.ForeignKey(Booster, on_delete=models.CASCADE)  # Связь с бустером
    quantity = models.IntegerField(default=0)  # Количество купленных бустеров

class Task(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, default="")  # Название задания
    url = models.URLField(default="")  # URL задания
    reward = models.PositiveIntegerField(default=1)  # Награда за выполнение задания

    def __str__(self):
        return self.name

class UserTask(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user_tasks')  # Ссылка на пользователя
    task = models.ForeignKey(Task, on_delete=models.CASCADE)  # Ссылка на задание
    completed_at = models.DateTimeField(auto_now_add=True)  # Время выполнения задания

    def __str__(self):
        return f"{self.user} - {self.task.name}"

class Wallet(models.Model):
    user_id = models.BigIntegerField(unique=True, null=True)
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    is_connected = models.BooleanField(default=False)

    def __str__(self):
        return f"WalletConnection(user_id={self.user_id}, is_connected={self.is_connected})"



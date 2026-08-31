from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.utils import timezone

# 1. ЖАНРЫ (для тегов "Песочница", "2D" и кнопок фильтрации)

class Genre(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название жанра")
    slug = models.SlugField(unique=True, verbose_name="URL-слаг")

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"

    def __str__(self):
        return self.name


class Collection(models.Model):
    title = models.CharField(max_length=100, verbose_name="Название подборки")
    slug = models.SlugField(unique=True, verbose_name="URL-слаг")

    class Meta:
        verbose_name = "Подборка"
        verbose_name_plural = "Подборки"

    def __str__(self):
        return self.title


class BaseMediaProduct(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание", blank=True)
    long_description = models.TextField(verbose_name="Детальное описание", blank=True)
    icon = models.ImageField(upload_to='icons/', verbose_name="Иконка", blank=True, null=True)
    cover = models.ImageField(upload_to='covers/', verbose_name="Обложка", blank=True, null=True)
    cover_hd = models.ImageField(upload_to='covers_hd/', verbose_name="HD Обложка", blank=True, null=True)
    trailer_file = models.FileField(upload_to='trailers/', blank=True, null=True, verbose_name="Файл трейлера")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    discount = models.IntegerField(default=0, verbose_name="Скидка (%)")
    release_date = models.DateField(verbose_name="Дата выхода", default=timezone.now)

    @property
    def discounted_price(self):
        if self.discount > 0:
            multiplier = Decimal(1) - (Decimal(self.discount) / Decimal(100))
            return (self.price * multiplier).quantize(Decimal('0.01'))
        return self.price

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

class Game(BaseMediaProduct):
    # Поля, которые ищет admin.py:
    genres = models.ManyToManyField(Genre, related_name='games', verbose_name="Жанры", blank=True)
    collections = models.ManyToManyField(Collection, related_name='game_products', verbose_name="Подборки", blank=True)
    is_game_of_the_week = models.BooleanField(default=False, verbose_name="Игра недели")
    is_not_on_steam = models.BooleanField(default=False, verbose_name="Нет в Steam")
    owners = models.ManyToManyField(User, related_name='purchased_games', blank=True)

    class Meta:
        verbose_name = "Игра"
        verbose_name_plural = "Игры"

    @property
    def get_icon_url(self):
        if self.icon and hasattr(self.icon, 'url'):
            return self.icon.url
        return '/media/default_icon.png'

class Screenshot(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='screenshots')
    image = models.ImageField(upload_to='screenshots/', max_length=250)

    def __str__(self):
        return f"Скриншот для {self.game.title}"


class Dlc(BaseMediaProduct):
    class Meta:
        verbose_name = "DLC"
        verbose_name_plural = "DLC"

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=150, blank=True)
    birth_date = models.DateField(blank=True, null=True)


class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        ACCEPTED = 'accepted', 'Принято'
        REJECTED = 'rejected', 'Отклонено'

    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='reviews')
    text = models.TextField(max_length=150)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    games = models.ManyToManyField(Game, blank=True)


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    games = models.ManyToManyField(Game, blank=True)


class ProfileComment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
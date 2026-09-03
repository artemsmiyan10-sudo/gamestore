from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Prefetch
from .models import Game, Genre, Collection
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.decorators.http import require_POST
import os

def home(request):
    # 1. Игра недели
    featured_game = Game.objects.filter(is_game_of_the_week=True).first()
    # 2. Все жанры для кнопок фильтра
    genres = Genre.objects.all()
    # 3. Считываем выбранный жанр из URL (?genre=slug)
    selected_genre_slug = request.GET.get('genre')
    # 4. Формируем queryset игр
    games_queryset = Game.objects.all()
    if selected_genre_slug:
        # .distinct() убирает дублирование игр при фильтрации по ManyToMany жанрам
        games_queryset = games_queryset.filter(genres__slug=selected_genre_slug).distinct()

    # 5. Подборки с оптимизированной загрузкой связанных жанров
    collections = Collection.objects.prefetch_related(
        Prefetch(
            'game_products', 
            queryset=games_queryset.prefetch_related('genres')
        )
    ).distinct()

    return render(request, 'store/index.html', {
        'featured_game': featured_game,
        'genres': genres,
        'collections': collections,
        'selected_genre_slug': selected_genre_slug,
    })

import os
from django.conf import settings
from mfs.models import Game, Dlc, Screenshot

# Собираем пути ко всем файлам, которые реально используются в базе
used_files = set()

def add_file(field):
    if field and hasattr(field, 'path') and os.path.exists(field.path):
        used_files.add(os.path.normpath(field.path))

for g in Game.objects.all():
    for attr in ['trailer_file', 'icon', 'cover_hd']:
        if hasattr(g, attr): add_file(getattr(g, attr))

for d in Dlc.objects.all():
    for attr in ['trailer_file', 'icon', 'cover_hd']:
        if hasattr(d, attr): add_file(getattr(d, attr))

for sc in Screenshot.objects.all():
    if hasattr(sc, 'image'): add_file(sc.image)

# Проходим по папке media и удаляем файлы, которых нет в базе
media_dir = settings.MEDIA_ROOT
deleted_count = 0

for root, dirs, files in os.walk(media_dir):
    for file in files:
        file_path = os.path.normpath(os.path.join(root, file))
        if file_path not in used_files:
            try:
                os.remove(file_path)
                deleted_count += 1
                print(f"Удален устаревший файл: {file}")
            except Exception as e:
                print(f"Ошибка удаления {file}: {e}")

print(f"Готово! Очищено файлов: {deleted_count}")


def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return render(request, 'store/game_detail.html', {
        'game': game
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('mfs:index') # Замените на имя вашей главной страницы

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_validate() if hasattr(form, 'is_validate') else form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('mfs:index')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()

    return render(request, 'store/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('mfs:index')

from .models import News
def news(request):
    news_list = News.objects.all()

    return render(
        request,
        "store/news.html",
        {
            "news_list": news_list
        }
    )

def remove_from_cart(request, game_id):
    cart = request.session.get('cart', [])
    if game_id in cart:
        cart.remove(game_id)
        request.session['cart'] = cart
    return redirect('mfs:cart_detail')

@login_required
def add_to_cart(request, game_id):
    cart = request.session.get('cart', [])
    if game_id not in cart:
        cart.append(game_id)
        request.session['cart'] = cart
        request.session.modified = True

    # Проверяем, пришел ли запрос через JavaScript (AJAX)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': len(cart) # Передаем количество товаров для счетчика в шапке
        })

    # Если это обычный переход по ссылке (на всякий случай)
    return redirect('mfs:cart_detail')


def cart_detail(request):
    cart = request.session.get('cart', [])
    
    if isinstance(cart, dict):
        game_ids = list(cart.keys())
    elif isinstance(cart, list):
        game_ids = cart
    else:
        game_ids = []

    # 1. Получаем товары в корзине
    cart_items = Game.objects.filter(id__in=game_ids)

    # 2. Берем 4 игры для блока "Вам может понравиться", исключая те, что уже в корзине
    recommended_games = Game.objects.exclude(id__in=game_ids)[:3]

    total_price = sum(game.discounted_price for game in cart_items)
    full_price = sum(game.price for game in cart_items)
    total_discount = full_price - total_price

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_discount': total_discount,
        'recommended_games': recommended_games,  # Передаем рекомендации в шаблон
    })

# Пример функции поиска в views.py
from django.http import JsonResponse
from .models import Game

def game_search_ajax(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'games': []})

    games = Game.objects.filter(title__icontains=query)[:5]
    results = []

    for game in games:
        # Жанры
        genres_str = ", ".join([g.name for g in game.genres.all()]) if hasattr(game, 'genres') else ""
        
        # Скидка и расчет цен
        discount = getattr(game, 'discount', 0)
        
        if discount > 0:
            if hasattr(game, 'old_price') and game.old_price:
                old_p = int(game.old_price)
                curr_p = int(game.price)
            else:
                old_p = int(game.price)
                # Приводим game.price к float для выполнения арифметической операции
                curr_p = int(float(game.price) * (1 - discount / 100))
        else:
            old_p = None
            curr_p = int(game.price)

        # Проверка эксклюзивности
        is_exclusive = getattr(game, 'is_exclusive', False)

        results.append({
            'id': game.id,
            'title': game.title,
            'price': curr_p,          # Рассчитанная цена со скидкой
            'old_price': old_p,       # Старая цена
            'discount': discount,     # Процент скидки
            'cover_url': game.cover.url if game.cover else '',
            'genres': genres_str,
            'is_exclusive': getattr(game, 'is_not_on_steam', False),
        })

    return JsonResponse({'games': results})

@login_required
def checkout(request):
    cart = request.session.get('cart', [])
    
    if isinstance(cart, dict):
        game_ids = list(cart.keys())
    else:
        game_ids = cart

    # Находим игры из корзины и привязываем их к текущему пользователю
    games = Game.objects.filter(id__in=game_ids)
    for game in games:
        game.owners.add(request.user)

    # Очищаем корзину после успешной покупки
    request.session['cart'] = []
    request.session.modified = True

    return redirect('mfs:library')


@login_required
def library(request):
    # Добавляем .order_by('title') для сортировки от A до Z
    user_games = request.user.purchased_games.all().order_by('title')

    return render(request, 'store/library.html', {
        'games': user_games
    })

@login_required
@require_POST
def remove_from_library(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    # Удаляем игру из ManyToMany связи пользователя (настройте под вашу модель)
    request.user.purchased_games.remove(game)
    return redirect('mfs:library')

# Замените сложную фильтрацию на простой запрос всех игр для проверки:
games = Game.objects.all()

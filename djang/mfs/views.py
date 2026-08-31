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

def game_search_ajax(request):
    query = request.GET.get('q', '').strip()
    results = []
    
    if len(query) >= 2: # Начинаем искать, если введено 2 и более символа
        # Ищем игры, содержащие запрос в названии (без учета регистра)
        games = Game.objects.filter(title__icontains=query)[:3]
        
        for game in games:
            # Безопасно получаем URL обложки
            cover_url = game.cover.url if game.cover else 'https://placeholder.com'
            
            # Высчитываем актуальную цену с учетом скидки (если метод прописан в модели)
            price = game.discounted_price if hasattr(game, 'discounted_price') else game.price

            results.append({
                'id': game.id,
                'title': game.title,
                'cover_url': cover_url,
                'price': f"{int(price)}₴",
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

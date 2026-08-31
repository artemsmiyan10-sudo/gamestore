from django.urls import path
from . import views

# Задаём пространство имён приложения (рекомендуется):
app_name = 'mfs'

urlpatterns = [
    path('', views.home, name='index'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:game_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:game_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('api/search/', views.game_search_ajax, name='game_search_ajax'),
    path('library/', views.library, name='library'),
    path('checkout/', views.checkout, name='checkout'),
    path('library/remove/<int:game_id>/', views.remove_from_library, name='remove_from_library')
]


from django.contrib import admin
from .models import Genre, Collection, Game, Dlc
from .models import Game, Screenshot
from .models import News

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}

class ScreenshotInline(admin.TabularInline):
    model = Screenshot
    extra = 4  # Количество готовых пустых полей для загрузки

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'discount', 'is_not_on_steam', 'is_game_of_the_week')
    list_editable = ('is_not_on_steam', 'is_game_of_the_week')
    filter_horizontal = ('genres', 'collections')
    inlines = [ScreenshotInline]

@admin.register(Dlc)
class DlcAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'discount')

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "created_at",
    )

    search_fields = (
        "title",
    )
from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'email',
        'first_name', 'last_name',
        'recipe_count', 'follows_count'
    )
    list_filter = ('email', 'last_name')
    search_fields = ('username', 'email')
    ordering = ('username', )
    empty_value_display = '-пусто-'

    @admin.display(description='Кол-во рецептов')
    def recipe_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Подписчики')
    def follows_count(self, obj):
        return obj.following.count()

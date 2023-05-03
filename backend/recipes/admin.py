from django.contrib import admin
from django.contrib.auth.models import Group

from .models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                     ShoppingCart, Tag)

admin.site.unregister(Group)


class TagInLine(admin.TabularInline):
    model = Recipe.tags.through
    min_num = 1
    verbose_name_plural = 'Добавьте теги рецепта'


class IngredientInLine(admin.TabularInline):
    model = Recipe.ingredients.through
    min_num = 1
    verbose_name_plural = 'Добавьте ингредиенты'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug', )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', )
    list_filter = ('name', )


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'author', 'image', )
    list_filter = ('author', 'name', 'tags', )
    inlines = (TagInLine, IngredientInLine, )


@admin.register(IngredientRecipe)
class IngredientRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount', )


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', )

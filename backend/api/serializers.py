from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe, User


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')

        return (request and request.user.is_authenticated
                and obj.following.filter(user=request.user).exists())


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeListSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')
        read_only_fields = (
            'id', 'email', 'username', 'first_name', 'last_name')

    def get_recipes(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        limit = request.GET.get('recipes_limit')
        queryset = obj.recipes.all()
        if limit:
            queryset = queryset[:int(limit)]

        return RecipeShortSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscribeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscribe
        fields = '__all__'
        validators = [UniqueTogetherValidator(
            queryset=Subscribe.objects.all(),
            fields=('user', 'author'))]

    def validate(self, data):
        if self.context['request'].user == data['author']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя')

        return data

    def to_representation(self, instance):
        return SubscribeListSerializer(instance).data


class IngredientRecipeReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'amount', 'measurement_unit')


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    author = UserSerializer(read_only=True)
    image = Base64ImageField(max_length=None)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_ingredients(self, obj):
        ingredients = IngredientRecipe.objects.filter(recipe=obj).all()

        return IngredientRecipeReadSerializer(ingredients, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')

        return (request and request.user.is_authenticated
                and obj.favorites.filter(user=request.user).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')

        return (request and request.user.is_authenticated
                and obj.shopping_cart.filter(user=request.user).exists())


class IngredientRecipeCreateSerializer(serializers.ModelSerializer):
    id = serializers.SlugRelatedField(
        queryset=Ingredient.objects.all(), slug_field='id')
    amount = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True)
    ingredients = IngredientRecipeCreateSerializer(many=True)
    author = UserSerializer(read_only=True)
    image = Base64ImageField(max_length=None)
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'name', 'image', 'text', 'cooking_time')

    def validate_tags(self, tags):
        tags_list = []
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Выберите хотя бы один тег'})
        for tag in tags:
            if not Tag.objects.filter(id=tag.id).exists():
                raise serializers.ValidationError(
                    'Нет такого тега')
            if tag.id in tags_list:
                raise serializers.ValidationError(
                    'Теги не могут повторяться')
            tags_list.append(tag.id)

        return tags

    def validate_ingredients(self, ingredients):
        ingredients_list = []
        if not ingredients:
            raise serializers.ValidationError(
                'Выберите хотя бы один ингредиент')
        for ingredient in ingredients:
            if ingredient in ingredients_list:
                raise serializers.ValidationError(
                    'Ингредиенты не могут повторяться')
            ingredients_list.append(ingredient)
            if int(ingredient.get('amount')) < 1:
                raise serializers.ValidationError(
                    'Укажите значение больше нуля')

        return ingredients

    def validate_cooking_time(self, cooking_time):
        if cooking_time < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше нуля')

        return cooking_time

    @staticmethod
    def add_ingredients(recipe, ingredients):
        IngredientRecipe.objects.bulk_create([IngredientRecipe(
            ingredient=ingredient.pop('id'), recipe=recipe,
            amount=ingredient.pop('amount')) for ingredient in ingredients])

    def create(self, validated_data):
        request = self.context.get('request')
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=request.user, **validated_data)
        recipe.tags.set(tags)
        self.add_ingredients(recipe=recipe, ingredients=ingredients)

        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        IngredientRecipe.objects.filter(recipe=instance).delete()
        tags = validated_data.pop('tags')
        instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients')
        self.add_ingredients(recipe=instance, ingredients=ingredients)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}

        return RecipeReadSerializer(instance, context=context).data


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        if user.favorites.filter(recipe=data['recipe']).exists():
            raise serializers.ValidationError('Рецепт уже в избранном')

        return data


class ShoppingCartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data['user']
        if user.shopping_cart.filter(recipe=data['recipe']).exists():
            raise serializers.ValidationError('Рецепт уже в корзине')

        return data

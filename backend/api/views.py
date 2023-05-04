from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscribe, User

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CustomUserSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, ShoppingCartSerializer,
                          SubscribeListSerializer, SubscribeSerializer,
                          TagSerializer)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = (filters.SearchFilter, )
    search_fields = ('name', )
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filterset_class = IngredientFilter


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter, )
    permission_classes = (IsAuthenticated, )
    pagination_class = CustomPagination
    search_fields = ('username', )
    http_method_names = ['patch', 'get', 'post', 'delete']

    @action(detail=False, methods=['get', 'patch'], url_path='me',
            permission_classes=[IsAuthenticated])
    def get_or_update_self(self, request):
        if request.method != 'GET':
            serializer = self.get_serializer(
                instance=request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(role=serializer.instance.role)
            return Response(serializer.data)

        serializer = self.get_serializer(request.user, many=False)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe',
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        subscribe_data = {
            'user': request.user.id,
            'author': author.id
        }

        if request.method == 'POST':
            serializer = SubscribeSerializer(
                author, data=subscribe_data,
                context={'request': request})
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data.get('user')
            author = serializer.validated_data.get('author')
            Subscribe.objects.create(user=user, author=author)

            return Response(
                serializer.data, status=status.HTTP_201_CREATED)

        get_object_or_404(
            Subscribe, user=request.user, author=author).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='subscriptions',
            permission_classes=[IsAuthenticated])
    def subscribe_list(self, request):
        queryset = User.objects.filter(following__user=request.user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={'request': request})

        return self.get_paginated_response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend, )
    permission_classes = (IsAuthorOrReadOnly, )
    pagination_class = CustomPagination
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @staticmethod
    def add_to(serializer_class, request, pk):
        context = {'request': request}
        recipe = get_object_or_404(Recipe, id=pk)
        data = {
            'user': request.user.id,
            'recipe': recipe.id
        }
        serializer = serializer_class(data=data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def del_from(model, request, pk):
        get_object_or_404(model, user=request.user,
                          recipe=get_object_or_404(Recipe, id=pk)).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorites(self, request, pk):
        if request.method == 'POST':
            return self.add_to(FavoriteSerializer, request, pk)

        return self.del_from(Favorite, request, pk)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.add_to(ShoppingCartSerializer, request, pk)
        return self.del_from(ShoppingCart, request, pk)

    @staticmethod
    def download_shopping_list(ingredients):
        shopping_list = 'Список покупок:\n'
        for ingredient in ingredients:
            shopping_list += (
                f'\n  - {ingredient["ingredient__name"]}: '
                f'{ingredient["amount"]} '
                f'({ingredient["ingredient__measurement_unit"]})'
            )
        filename = 'shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename = {filename}'

        return response

    @action(detail=False, methods=['get'], url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated])
    def make_shopping_list(self, request):
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_cart__user=request.user).order_by(
            'ingredient__name').values(
            'ingredient__name', 'ingredient__measurement_unit').annotate(
            amount=Sum('amount'))

        return self.download_shopping_list(ingredients)

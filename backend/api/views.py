from djoser.views import UserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from recipes.models import Ingredient, Tag
from users.models import Subscribe, User

from .serializers import (CustomUserSerializer, IngredientSerializer,
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


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    filter_backends = (filters.SearchFilter, )
    search_fields = ('username', )
    http_method_names = ['patch', 'get', 'post', 'delete']

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def get_or_update_self(self, request):
        if request.method != 'GET':
            serializer = self.get_serializer(
                instance=request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(role=serializer.instance.role)
            return Response(serializer.data)

        serializer = self.get_serializer(request.user, many=False)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
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

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscribe_list(self, request):
        queryset = User.objects.filter(following__user=request.user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={'request': request})

        return self.get_paginated_response(serializer.data)

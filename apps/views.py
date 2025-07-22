import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from apps.serializers import *


@extend_schema(tags=['shops'])
class ShopCreateAPIView(generics.CreateAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


@extend_schema(tags=['shops'])
class ShopListAPIView(generics.ListAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


@extend_schema(tags=['category'])
class CategoryCreatApi(generics.CreateAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer


@extend_schema(tags=['category'])
class CategoryListApi(generics.ListAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer


@extend_schema(tags=['category'])
class CategoryDetailApi(generics.DestroyAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def perform_destroy(self, instance):
        instance.delete()


@extend_schema(tags=['category'])
class CategoryUpdateApi(generics.UpdateAPIView):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs['id']

        try:
            return queryset.get(id=uuid.UUID(str(lookup_value)))
        except (ValueError, AttributeError):
            return get_object_or_404(queryset, pk=int(lookup_value))


@extend_schema(tags=['Unit'])
class UnitCreateApi(generics.CreateAPIView):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer


@extend_schema(tags=['Role'])
class RoleCreateApi(generics.CreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


@extend_schema(tags=['Role'])
class RoleListApi(generics.ListAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


@extend_schema(tags=['Role'])
class RoleDetailApi(generics.DestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def perform_destroy(self, instance):
        instance.delete()

@extend_schema(tags=['Role'])
class RoleUpdateApi(generics.UpdateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

@extend_schema(tags=['product'])
class ProductCreateApi(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
@extend_schema(tags=['product'])
class ProductListApi(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

@extend_schema(tags=['product'])
class ProductDetailApi(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
@extend_schema(tags=['product'])
class ProductUpdateApi(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'





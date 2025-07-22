from rest_framework import serializers
from .models import ProductCategory, Product, Shop, User, Unit, RolePermission, Role


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['name', 'location', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = [ 'name', 'shop', 'created_at']
        read_only_fields = ['id', 'created_at']


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['name']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['name']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'cost_price',
            'unit', 'category', 'barcode', 'image_url',
            'is_active', 'shop', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

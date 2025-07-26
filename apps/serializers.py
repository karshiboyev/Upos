import json

from django.contrib.auth.hashers import make_password
from redis import Redis
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import Serializer, ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import ProductCategory, Product, Shop, User, Unit, RolePermission, Role, Transaction, StockMovement


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id','user_id','name', 'location', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'shop', 'created_at']
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
            'id', 'name', 'description', 'price', 'cost_price',
            'unit', 'category', 'barcode', 'image_url',
            'is_active', 'shop',  'created_at', 'updated_at'
        ]
        read_only_fields = ['id',  'created_at', 'updated_at']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone_number', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionBrcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'barcode', 'name', 'description', 'price', 'image_url', 'category_id', 'unit_id', 'shop_id', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'barcode', 'price', 'image_url', 'category_id', 'unit_id', 'shop_id',
            'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PurchaseItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0.001)


class PurchaseSerializer(serializers.Serializer):
    items = PurchaseItemSerializer(many=True)  # Bir nechta mahsulot uchun
    payment_type = serializers.ChoiceField(choices=[('cash', 'Naqt'), ('debt', 'Qarz')])
    customer_phone = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=True
    )
    customer_name = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        trim_whitespace=True
    )

    def validate(self, data):
        if data['payment_type'] == 'debt':
            if not data.get('customer_phone'):
                raise serializers.ValidationError({"customer_phone": "Qarz uchun telefon raqami kerak"})
            if not data.get('customer_name'):
                raise serializers.ValidationError({"customer_name": "Qarz uchun ism kerak"})
        return data


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'quantity', 'movement_type', 'shop', 'reason', 'user', 'created_at']
        read_only_fields = ['id', 'user_id', 'created_at']


class SercherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id','name','price']


class VerifyOtpSerializer(Serializer):
    verify_pk = CharField(max_length=255 , required=True)
    code = IntegerField( required=True)

    def validate(self, attrs):
        redis = Redis(decode_responses=True)
        pk = attrs.get("verify_pk")
        code = attrs.get("code")
        data = redis.mget(pk)[0]
        if data:
            data = json.loads(data)
            self.phone_number = data.get("data").get("phone_number")
            self.password = data.get("data").get("password")
            self.full_name = data.get("data").get("full_name") # None
            verify_code = data.get("code")
            if verify_code != code:
                raise ValidationError("Tastiqlash code xato !")
        return attrs

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.phone_number
        return token


class UserModelSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = 'id',"full_name" , "phone_number" , "password"

    def validate_phone_number(self , value):
        query = User.objects.filter(phone_number=value)
        if query.exists():
            raise ValidationError("Bunday Telefon raqam mavjud")
        return value

    def validate_password(self , value):
        return make_password(value)


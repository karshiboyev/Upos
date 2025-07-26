import json
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import transaction
from redis import Redis
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import Serializer, ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import ProductCategory, Product, Shop, User, Unit, Role, StockMovement, Customer, Transaction, \
    TransactionItem


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'user_id', 'name', 'location', 'is_active', 'created_at', 'updated_at']
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
            'id', 'name', 'description', 'price', 'cost_price','user_id',
            'unit', 'category', 'barcode', 'image_url',
            'is_active', 'shop', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone_number', 'is_active','is_shop','is_staff'
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
        fields = ['id', 'name', 'price']


class VerifyOtpSerializer(Serializer):
    verify_pk = CharField(max_length=255, required=True)
    code = IntegerField(required=True)

    def validate(self, attrs):
        redis = Redis(decode_responses=True)
        pk = attrs.get("verify_pk")
        code = attrs.get("code")
        data = redis.mget(pk)[0]
        if data:
            data = json.loads(data)
            self.phone_number = data.get("data").get("phone_number")
            self.password = data.get("data").get("password")
            self.full_name = data.get("data").get("full_name")  # None
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
        fields = 'id', "full_name", "phone_number", "password"

    def validate_phone_number(self, value):
        query = User.objects.filter(phone_number=value)
        if query.exists():
            raise ValidationError("Bunday Telefon raqam mavjud")
        return value

    def validate_password(self, value):
        return make_password(value)


class CreateTransactionSerializer(serializers.Serializer):
    """
    Serializer for creating transactions based on your JSON structure
    """
    products = serializers.ListField(
        child=serializers.DictField()
    )
    paymentType = serializers.CharField(max_length=20)
    debtor = serializers.DictField(required=False, allow_null=True)

    def validate_products(self, value):
        if not value:
            raise serializers.ValidationError("Products list cannot be empty")

        for i, product_data in enumerate(value):
            # Debug: print what we received
            print(f"Product {i}: {product_data}")

            required_fields = ['id', 'name', 'count', 'shopId']
            for field in required_fields:
                if field not in product_data:
                    raise serializers.ValidationError(f"Missing field: {field} in product {i}")

            # Validate data types
            try:
                int(product_data['count'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Product count must be integer in product {i}")

        return value

    def validate_paymentType(self, value):
        valid_types = ['cash', 'card', 'debt', 'mixed']
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid payment type. Must be one of: {valid_types}")
        return value

    def validate(self, attrs):
        payment_type = attrs.get('paymentType')
        debtor = attrs.get('debtor')

        if payment_type == 'debt' and not debtor:
            raise serializers.ValidationError("Debtor info required for debt payments")

        if debtor and ('phoneNumber' not in debtor or 'FullName' not in debtor):
            raise serializers.ValidationError("Debtor must have phoneNumber and FullName")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        products_data = validated_data['products']
        payment_type = validated_data['paymentType']
        debtor_data = validated_data.get('debtor')
        user = self.context['request'].user

        # Get shop from first product
        shop_id = products_data[0]['shopId']

        # Handle customer/debtor
        customer = None
        if debtor_data:
            customer, created = Customer.objects.get_or_create(
                phone_number=debtor_data['phoneNumber'],
                shop_id=shop_id,
                defaults={
                    'full_name': debtor_data['FullName'],
                    'total_debt': Decimal('0.00')
                }
            )

        # Calculate totals
        total_price = Decimal('0.00')
        total_cost = Decimal('0.00')
        items_data = []

        for product_data in products_data:
            try:
                product = Product.objects.get(id=product_data['id'])
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Product {product_data['id']} not found")

            quantity = int(product_data['count'])

            # Check stock
            if product.stock < quantity:
                raise serializers.ValidationError(
                    f"Not enough stock for {product.name}. Available: {product.stock}"
                )

            item_total = product.price * quantity
            item_cost = product.cost_price * quantity

            total_price += item_total
            total_cost += item_cost

            items_data.append({
                'product': product,
                'quantity': quantity,
                'price_at_sale': product.price,
                'cost_at_sale': product.cost_price
            })

        # Create transaction
        transaction_obj = Transaction.objects.create(
            shop_id=shop_id,
            user=user,
            customer=customer,
            total_price=total_price,
            cost_total=total_cost,
            profit=total_price - total_cost,
            payment_type=payment_type
        )

        # Create items and update stock
        for item_data in items_data:
            TransactionItem.objects.create(
                transaction=transaction_obj,
                product=item_data['product'],
                quantity=item_data['quantity'],
                price_at_sale=item_data['price_at_sale'],
                cost_at_sale=item_data['cost_at_sale'],
                discount=Decimal('0.00')
            )

            # Update stock
            product = item_data['product']
            product.stock -= item_data['quantity']
            product.save()

        # Update debt if needed
        if payment_type == 'debt' and customer:
            customer.total_debt += total_price
            customer.save()

        return {
            'transaction_id': str(transaction_obj.id),
            'total_price': float(total_price),
            'payment_type': payment_type,
            'status': 'success'
        }
import json
from django.db import transaction as db_transaction
from django.contrib.auth.hashers import make_password
from redis import Redis
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import Serializer, ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import  Product, Shop, User,  StockMovement, Customer, TransactionItem, \
    Transaction


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'user_id', 'name', 'location', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']




class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'cost_price', 'user_id',
            'unit',  'barcode', 'image_url', 'quantity',
            'is_active', 'shop', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone_number', 'is_active', 'is_shop', 'is_staff'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PurchaseItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0.001)


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


class TransactionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionItem
        fields = '__all__'


class TransactionListSerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Transaction
        fields = '__all__'


class ForgotPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        query = User.objects.filter(phone_number=value)
        if not query.exists():
            raise ValidationError("Bunday Telefon raqam mavjud emas")
        return value


class ForgotUpdatePasswordSerializer(Serializer):
    password = CharField(max_length=20, required=True)
    confirm_password = CharField(max_length=20, required=True)
    verify_pk = CharField(required=True, max_length=255)

    def validate(self, attrs):
        redis = Redis(decode_responses=True)
        pk = attrs.get("verify_pk")
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")
        data = redis.mget(pk)[0]
        if data:
            if password != confirm_password:
                raise ValidationError("Password va Confirm password tasdiqlamadi")

            data = json.loads(data)
            self.phone_number = data.get("data").get("phone_number")
            self.password = password
            User.objects.filter(phone_number=self.phone_number).update(password=make_password(password))
            return attrs
        else:
            raise ValidationError("Bu sòrovni amalga oshirish uchun tasdiqlanmagan !")


class ProductPurchaseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    count = serializers.IntegerField()
    shop_id = serializers.UUIDField()
    user_id = serializers.UUIDField()


class DebtorSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    full_name = serializers.CharField()


class TransactionItemDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name')
    unit = serializers.CharField(source='product.unit')

    class Meta:
        model = TransactionItem
        fields = ['product_name', 'unit', 'quantity', 'price_at_sale']


class TransactionSerializer(serializers.ModelSerializer):
    items = TransactionItemDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'


class TransactionCreateSerializer(serializers.Serializer):
    products = ProductPurchaseSerializer(many=True)
    payment_type = serializers.ChoiceField(choices=Transaction.PAYMENT_TYPES)
    debtor = DebtorSerializer(required=False, allow_null=True)

    def create(self, validated_data):
        products_data = validated_data.pop("products")
        payment_type = validated_data.get("payment_type")
        debtor_data = validated_data.get("debtor", None)

        if not products_data:
            raise serializers.ValidationError("Mahsulotlar ro'yxati bo'sh bo'lishi mumkin emas.")

        # 1. Har doim birinchi mahsulotdan shop va user ni olamiz
        first_item = products_data[0]
        try:
            shop = Shop.objects.get(id=first_item["shop_id"])
            user = User.objects.get(id=first_item["user_id"])
        except Shop.DoesNotExist:
            raise serializers.ValidationError({"shop_id": "Berilgan shop topilmadi."})
        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "Berilgan user topilmadi."})

        customer = None
        if payment_type == 'debt':
            if not debtor_data:
                raise serializers.ValidationError({"debtor": "Debt to'lovi uchun debtor ma'lumotlari kerak."})
            phone = debtor_data.get("phone_number")
            full_name = debtor_data.get("full_name")

            customer, _ = Customer.objects.get_or_create(
                phone_number=phone,
                shop=shop,
                defaults={"full_name": full_name}
            )
        elif debtor_data:
            raise serializers.ValidationError({"debtor": "Debtor faqat payment_type = 'debt' bo'lganda kerak bo'ladi."})

        total_price = 0
        cost_total = 0
        profit_total = 0

        with db_transaction.atomic():
            # 2. Transactionni boshlang'ich qiymatlar bilan yaratamiz
            transaction = Transaction.objects.create(
                shop=shop,
                user=user,
                customer=customer,
                payment_type=payment_type,
                total_price=0,  # vaqtincha
                cost_total=0,
                profit=0
            )

            for item in products_data:
                try:
                    product = Product.objects.get(id=item["id"])
                except Product.DoesNotExist:
                    raise serializers.ValidationError({"product_id": f"Mahsulot topilmadi: {item['id']}"})

                quantity = item["count"]

                # 1. Noldan katta bo'lishi kerak
                if quantity <= 0:
                    raise serializers.ValidationError({
                        "count": f"{product.name} uchun count 0 dan katta bo'lishi kerak."
                    })

                # 2. Agar zaxira yetarli bo'lmasa, avtomatik kirim qilamiz
                if product.quantity < quantity:
                    missing = quantity - product.quantity
                    print(f"[INFO] {product.name}: Zaxira yetarli emas. {missing} dona avtomatik kirim qilinyapti.")
                    product.quantity += missing  # avtomatik kirim
                    # Ehtimol: bu joyda siz StockLog modelga kirim yozishingiz mumkin

                # 3. Endi zaxiradan ayiramiz
                product.quantity -= quantity
                product.save()

                price = product.price
                cost = product.cost_price

                TransactionItem.objects.create(
                    transaction=transaction,
                    product=product,
                    quantity=quantity,
                    price_at_sale=price,
                    cost_at_sale=cost
                )

                total_price += price * quantity
                cost_total += cost * quantity
                profit_total += (price - cost) * quantity

            # 5. Transactionni yangilaymiz
            transaction.total_price = total_price
            transaction.cost_total = cost_total
            transaction.profit = profit_total
            transaction.save()

            # 6. Agar debt bo'lsa — mijozga qarzdorlik qo‘shamiz
            if payment_type == 'debt' and customer:
                customer.total_debt += total_price
                customer.save()

        return transaction

class ProductBarcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

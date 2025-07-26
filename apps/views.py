import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import OuterRef
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import get_object_or_404, CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.models import Customer, TransactionItem, Payment
from apps.permissions import IsActiveUser
from apps.serializers import *
from apps.tasks import start_daily_deduction, deduct_daily_fee
import uuid
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.models import User
from apps.serializers import VerifyOtpSerializer, CustomTokenObtainPairSerializer, \
    UserModelSerializer
from apps.tasks import send_code


@extend_schema(tags=['shops'])
class ShopCreateAPIView(generics.CreateAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Shop yaratish
        shop = serializer.save()

        # Hozirgi foydalanuvchining is_shop maydonini True qilish
        user = self.request.user
        user.shop_id = shop
        user.save()

        return shop


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


@extend_schema(tags=['profile'])
class ProfileListApi(generics.ListAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)


@extend_schema(tags=['transaction'])
class TransactionBrcode(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = TransactionBrcodeSerializer


@extend_schema(tags=['transaction'])
class TransactionList(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = TransactionListSerializer


# views.py
@extend_schema(tags=['transaction'])
class ProductSearchAPI(APIView):
    def get(self, request):
        barcode = request.query_params.get('barcode')
        name = request.query_params.get('name')

        products = Product.objects.all()
        if barcode:
            products = products.filter(barcode=barcode)
        if name:
            products = products.filter(name__icontains=name)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=['transaction'],
    request=PurchaseSerializer,
    responses={201: PurchaseSerializer}
)
class PurchaseAPI(GenericAPIView):
    permission_classes = [IsActiveUser]
    serializer_class = PurchaseSerializer  # Serializer klassini qo'shamiz

    @transaction.atomic
    def post(self, request):
        # Foydalanuvchi shopini tekshirish (filter orqali birinchi faol do'konni olamiz)
        try:
            user_shop = Shop.objects.filter(
                user_id=request.user.id,
                is_active=True
            ).first()  # Birinchi topilgan faol do'konni olamiz

            if not user_shop:
                return Response({"error": "Sizning faol do'koningiz topilmadi"}, status=403)

        except Exception as e:
            return Response({"error": f"Do'kon ma'lumotlarini olishda xatolik: {str(e)}"}, status=500)

        serializer = self.get_serializer(data=request.data)  # DRF-ni serializer metodidan foydalanish
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        errors = []
        transaction_items = []
        total_amount = Decimal('0')
        cost_total = Decimal('0')
        customer = None

        # Mahsulotlarni tekshirish
        for item in data['items']:
            try:
                product = Product.objects.select_for_update().get(
                    id=item['product_id'],
                    shop_id=user_shop.id,
                    is_active=True
                )
                quantity = Decimal(str(item['quantity']))

                if quantity <= 0:
                    errors.append({
                        'product_id': item['product_id'],
                        'message': "Miqdor musbat son bo'lishi kerak"
                    })
                    continue

                if product.quantity < quantity:
                    errors.append({
                        'product_id': product.id,
                        'message': f"Yetarli mahsulot yo'q. Qolgan: {product.quantity}"
                    })
                    continue

                if product.price <= 0:
                    errors.append({
                        'product_id': product.id,
                        'message': "Mahsulot narxi noto'g'ri"
                    })
                    continue

                item_total = product.price * quantity
                item_cost = product.cost_price * quantity

                total_amount += item_total
                cost_total += item_cost

                transaction_items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': product.price,
                    'cost_price': product.cost_price,
                    'total': item_total,
                    'unit': product.unit.name if product.unit else 'dona'
                })

            except Product.DoesNotExist:
                errors.append({
                    'product_id': item['product_id'],
                    'message': "Mahsulot topilmadi yoki faol emas"
                })
            except Exception as e:
                errors.append({
                    'product_id': item.get('product_id', 'unknown'),
                    'message': f"Xatolik yuz berdi: {str(e)}"
                })

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        if total_amount <= 0:
            return Response(
                {"error": "Umumiy summa noto'g'ri"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Qarz mijozini yaratish yoki yangilash
        if data.get('payment_type') == 'debt':
            if not data.get('customer_phone'):
                return Response(
                    {"error": "Qarz uchun mijoz telefon raqami kerak"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            customer, created = Customer.objects.get_or_create(
                phone_number=data['customer_phone'],
                shop_id=user_shop.id,
                defaults={
                    'full_name': data.get('customer_name', ''),
                    'total_debt': Decimal('0')
                }
            )

            if not created and data.get('customer_name'):
                customer.full_name = data['customer_name']

            customer.total_debt += total_amount
            customer.save()

        # Transaksiyani yaratish
        try:
            main_transaction = Transaction.objects.create(
                total_price=total_amount,
                cost_total=cost_total,
                profit=total_amount - cost_total,
                payment_type=data['payment_type'],
                customer=customer,
                user=request.user,
                shop_id=user_shop.id,
                status='completed'
            )
        except Exception as e:
            return Response(
                {"error": f"Transaksiya yaratishda xatolik: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Transaksiya elementlarini yaratish
        try:
            for item in transaction_items:
                TransactionItem.objects.create(
                    transaction=main_transaction,
                    product=item['product'],
                    product_name=item['product'].name,
                    product_price=item['price'],
                    cost_at_sale=item['cost_price'],
                    quantity=item['quantity'],
                    total=item['total'],
                    unit=item['unit']
                )

                item['product'].quantity -= item['quantity']
                item['product'].save()

        except Exception as e:
            return Response(
                {"error": f"Transaksiya elementlarini yaratishda xatolik: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Javobni tayyorlash
        response_data = {
            "success": True,
            "transaction_id": main_transaction.id,
            "total_amount": str(total_amount),
            "cost_total": str(cost_total),
            "profit": str(total_amount - cost_total),
            "payment_type": data['payment_type'],
            "created_at": main_transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "items": [{
                "product_id": item['product'].id,
                "name": item['product'].name,
                "price": str(item['price']),
                "cost_price": str(item['cost_price']),
                "quantity": str(item['quantity']),
                "total": str(item['total']),
                "unit": item['unit']
            } for item in transaction_items],
            "customer": {
                "id": customer.id,
                "name": customer.full_name,
                "phone": customer.phone_number,
                "total_debt": str(customer.total_debt)
            } if customer else None
        }

        return Response(response_data, status=status.HTTP_201_CREATED)
@extend_schema(tags=["transaction"])
class TransactionHistory(generics.ListAPIView):
    queryset = Transaction


@extend_schema(tags=["transaction"])
class TransactionItemsHistory(generics.ListAPIView):
    queryset = TransactionItem


@extend_schema(tags=["Pyment"])
# PYMENT
class PaymentView(APIView):
    def post(self, request):
        user = request.user
        amount = float(request.data.get('amount', 0))

        # To'lovni yaratamiz
        payment = Payment.objects.create(
            user=user,
            amount=amount,
            payment_status='paid',
            description='To\'lov qabul qilindi'
        )

        # Foydalanuvchi balansini yangilaymiz
        user.balance += amount
        user.is_active = True
        user.save()

        # Kunlik yechishni boshlaymiz
        start_daily_deduction().delay(user.id)

        return Response({
            "success": True,
            "message": f"To'lov qabul qilindi! Yangi balans: {user.balance} so'm",
            "new_balance": user.balance
        })


@extend_schema(tags=["Pyment"])
# PYMENT
class DailyDeductionAPI(APIView):
    def get(self, request):
        try:
            deduct_daily_fee()
            active_users = User.objects.filter(is_active=True)
            result = {
                "success": True,
                "message": "Kunlik to'lovlar muvaffaqiyatli amalga oshirildi",
                "active_users_count": active_users.count(),
                "updated_users": [
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "new_balance": user.balance,
                        "status": "active" if user.is_active else "inactive"
                    }
                    for user in active_users
                ]
            }
            return Response(result)

        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=400)  # #


@extend_schema(tags=["StockMovement"], responses={201: StockMovementSerializer})
class StockMovementAPI(CreateAPIView):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsActiveUser]


@extend_schema(tags=["StockMovement"])
class StockMovementListAPI(APIView):
    def get(self, request):
        try:
            shop_id = request.query_params.get('shop_id')
            product_id = request.query_params.get('product_id')

            queryset = StockMovement.objects.all()

            if shop_id:
                queryset = queryset.filter(shop_id=shop_id)
            if product_id:
                queryset = queryset.filter(product_id=product_id)

            movements = queryset.order_by('-created_at')[:5]  # Oxirgi 5 tasi

            results = []
            for m in movements:
                results.append({
                    'id': str(m.id),
                    'date': m.created_at.strftime('%Y-%m-%d %H:%M'),
                    'product': m.product.name,
                    'quantity': m.quantity,
                    'type': m.get_movement_type_display(),
                    'reason': m.reason,
                    'user': m.user.full_name if m.user else None,
                    'shop': m.shop.name
                })

            return Response({
                'success': True,
                'count': len(results),
                'results': results
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)


@extend_schema(
    tags=["Search"],
    parameters=[
        OpenApiParameter(
            name='name',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Search term to filter products by name (case-insensitive)',
            required=False,
        )
    ]
)
class SearchAPI(generics.ListAPIView):
    serializer_class = SercherSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        search_term = self.request.query_params.get('name', '')
        print(f"Search term: {search_term}")  # Debug
        queryset = Product.objects.filter(name__icontains=search_term).only('id', 'name', 'price')
        print(f"Queryset: {list(queryset.values('id', 'name', 'price'))}")  # Debug
        return queryset


@extend_schema(tags=['Register'])
class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            message = "Bu Eskiz dan test"
            pk = str(uuid.uuid4())
            send_code.delay(request.data, message=message, pk=pk)
            return Response({"message": "tastiqlash uchun code yuborilidi !", "pk": pk}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e


@extend_schema(tags=['Register'])
class VerifyLoginOtpView(TokenObtainPairView):
    serializer_class = VerifyOtpSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = {
                "phone_number": serializer.phone_number,
                "password": serializer.password  # hash
            }
            serializer = CustomTokenObtainPairSerializer(data=data)
            serializer.is_valid()
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Register'])
class VerifyRegisterOtpView(GenericAPIView):
    serializer_class = VerifyOtpSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = {
                "phone_number": serializer.phone_number,
                "password": serializer.password,
                "full_name": serializer.full_name,
            }
            user = User.objects.create(**data)
            serializer = UserModelSerializer(instance=user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterAPIView(GenericAPIView):
    serializer_class = UserModelSerializer

    def post(self, request):
        serializer = UserModelSerializer(data=request.data)
        if serializer.is_valid():
            message = "Bu Eskiz dan test"
            pk = str(uuid.uuid4())
            send_code.delay(user_data=serializer.data, message=message, pk=pk)
            return Response({"message": "tastiqlash uchun code yuborilidi !", "pk": pk}, status=status.HTTP_200_OK)
        return Response(serializer.errors)

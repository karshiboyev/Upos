from django.db.models.aggregates import Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import CreateAPIView, ListAPIView, DestroyAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from apps.permissions import IsActiveUser
from apps.serializers import *
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
class ShopCreateAPIView(CreateAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Shop yaratish
        shop = serializer.save()

        # Hozirgi foydalanuvchining is_shop maydonini True qilish
        user = self.request.user
        user.is_shop = True
        user.shop_id = shop.id
        user.save()

        return shop


@extend_schema(tags=['shops'])
class ShopListAPIView(ListAPIView):
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Shop.objects.filter(user_id=self.request.user.id)


@extend_schema(tags=['product'])
class ProductCreateApi(CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


@extend_schema(tags=['product'])
class ProductListApi(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(shop_id=self.request.user.shop_id)


@extend_schema(tags=['product'])
class ProductDetailApi(DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'


@extend_schema(tags=['product'])
class ProductUpdateApi(UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
@extend_schema(tags=['product'])
class ProductBarcodeApi(ListAPIView):
    serializer_class = ProductBarcodeSerializer


@extend_schema(tags=['profile'])
class ProfileListApi(ListAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)


@extend_schema(tags=['product'])
class ProductBarcodeApi(RetrieveAPIView):
    serializer_class = ProductBarcodeSerializer
    # permission_classes = [IsAuthenticated]
    queryset = Product.objects.all()
    lookup_field = 'barcode'


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
            description='Search term to filter products by name (case-insensitive)',
            required=False,
        )
    ]
)
class SearchAPI(ListAPIView):
    serializer_class = SercherSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        search_term = self.request.query_params.get('name', '')
        if self.request.user.is_authenticated and Product.objects.filter(user_id=self.request.user.id).exists():
            queryset = Product.objects.filter(
                user_id=self.request.user.id,
                name__icontains=search_term
            ).only('id', 'name', 'price')
            return queryset
        return Product.objects.none()


@extend_schema(tags=['auth'])
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


@extend_schema(tags=['auth'])
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


@extend_schema(tags=['auth'])
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

            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            serializer = UserModelSerializer(instance=user)
            response_data = serializer.data.copy()
            response_data["tokens"] = {
                "access": str(access_token),
                "refresh": str(refresh),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Register'])
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


@extend_schema(tags=['Transaction'])
class TransactionsList(generics.ListAPIView):
    serializer_class = TransactionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user.id
        ).annotate(
            items_count=Count('items')  # related_name="items"
        ).prefetch_related('items')


@extend_schema(tags=['auth'])
class ForgotPasswordAPIView(GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(phone_number=request.data.get('phone_number'))
            message = "Bu Eskiz dan test"
            pk = str(uuid.uuid4())
            user = UserModelSerializer(instance=user).data
            send_code.delay(user_data=user, message=message, pk=pk)
            return Response({"message": "tastiqlash uchun code yuborilidi !", "pk": pk}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['auth'])
class ForgotOTPdAPIView(GenericAPIView):
    serializer_class = VerifyOtpSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response({"verify_pk": request.data.get("verify_pk")}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['auth'])
class ForgotUpdatePasswordAPIView(GenericAPIView):
    serializer_class = ForgotUpdatePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(phone_number=serializer.phone_number)
            user.set_password(serializer.password)
            user.save()
            return Response({"message": "Hisobni passwordi mofaqiyatli òzgartirildi"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Transaction'])
class TransactionCreateAPIView(GenericAPIView):
    serializer_class = TransactionCreateSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            try:
                transaction = serializer.save()
                return Response(
                    {
                        "success": True,
                        "message": "Order muvaffaqiyatli yaratildi",
                        "data": TransactionSerializer(transaction).data  # ✅ TO‘G‘RI SERIALIZER
                    },
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {
                        "success": False,
                        "message": f"Xatolik yuz berdi: {str(e)}"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {
                "success": False,
                "message": "Ma'lumotlar noto'g'ri",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

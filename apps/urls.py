from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView, TokenRefreshView

from apps.views import ShopCreateAPIView, ShopListAPIView, ProductCreateApi, \
    ProductListApi, ProductDetailApi, ProductUpdateApi, ProfileListApi, \
    SearchAPI, RegisterAPIView, VerifyRegisterOtpView, CustomTokenObtainPairView, VerifyLoginOtpView, \
    TransactionsList, ForgotPasswordAPIView, ForgotOTPdAPIView, ForgotUpdatePasswordAPIView, TransactionCreateAPIView, \
    ProductBarcodeApi, InvoiceView
from apps.views_analytics import AnalyticsAPI

urlpatterns = [
    # JWT
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # SHOP
    path('api/v1/shop/create/', ShopCreateAPIView.as_view()),
    path('api/v1/shop/list/', ShopListAPIView.as_view()),

]
urlpatterns += [
    # Profile and password
    path('api/v1/profile/', ProfileListApi.as_view())
]

urlpatterns += [
    # PRODUCTS
    path('api/v1/products/creat/', ProductCreateApi.as_view()),
    path('api/v1/products/list/', ProductListApi.as_view()),
    path('api/v1/products/<str:id>/delete/', ProductDetailApi.as_view()),
    path('api/v1/products/<str:id>/update/', ProductUpdateApi.as_view()),
    path('api/v1/product/barcode/<str:barcode>/', ProductBarcodeApi.as_view())

]

urlpatterns += [
    # Serche
    path('api/v1//sercher/', SearchAPI.as_view()),

]

# ============================== Auth ============================================
urlpatterns += [
    path('api/v1/register', RegisterAPIView.as_view(), name='token_obtain_pair'),
    path('api/v1/register/verifyOtp', VerifyRegisterOtpView.as_view(), name='token_obtain_pair'),
    path('api/v1/login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/login/verifyOTP', VerifyLoginOtpView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/forgot', ForgotPasswordAPIView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/forgot/OTP', ForgotOTPdAPIView.as_view(), name='forgot-otp'),
    path('api/v1/auth/forgot/update/password', ForgotUpdatePasswordAPIView.as_view(), name='forgot-otp'),
    path('api/v1/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
]
# Transaction
urlpatterns += [
    path('api/v1/transaction/', TransactionCreateAPIView.as_view(), name='purchase'),
    path('api/transaction/historiy/', TransactionsList.as_view())
]

urlpatterns += [
    path("api/analytics/", AnalyticsAPI.as_view(), name="analytics"),
    path('api/v1/invioce/<str:invoice_code>/',InvoiceView.as_view())
]

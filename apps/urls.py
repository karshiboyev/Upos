from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView, TokenRefreshView

from apps.views import ShopCreateAPIView, ShopListAPIView, ProductCreateApi, \
    ProductListApi, ProductDetailApi, ProductUpdateApi, ProfileListApi,  StockMovementListAPI, \
    SearchAPI, RegisterAPIView, VerifyRegisterOtpView, CustomTokenObtainPairView, VerifyLoginOtpView, \
    TransactionsList, ForgotPasswordAPIView, ForgotOTPdAPIView, ForgotUpdatePasswordAPIView, TransactionCreateAPIView, \
    ProductBarcodeApi
from apps.views_analytics import AnalyticsAPI

urlpatterns = [
    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # SHOP
    path('api/shop/create/', ShopCreateAPIView.as_view()),
    path('api/shop/list/', ShopListAPIView.as_view()),

]
urlpatterns += [
    # Profile and password
    path('api/profile/', ProfileListApi.as_view())
]

urlpatterns += [
    # PRODUCTS
    path('api/products/creat/', ProductCreateApi.as_view()),
    path('api/products/list/', ProductListApi.as_view()),
    path('api/products/<str:id>/delete/', ProductDetailApi.as_view()),
    path('api/products/<str:id>/update/', ProductUpdateApi.as_view()),
    path('api/product/barcode/<str:barcode>/',ProductBarcodeApi.as_view())

]

urlpatterns += [
    # # STOCKMOVEMENT
    # path('api/stock/movement/post/', StockMovementAPI.as_view()),
    # path('api/stock/movement/list/', StockMovementListAPI.as_view()),

    # Serche
    path('api/sercher/', SearchAPI.as_view()),

]

# ============================== Auth ============================================
urlpatterns += [
    path('register', RegisterAPIView.as_view(), name='token_obtain_pair'),
    path('register/verifyOtp', VerifyRegisterOtpView.as_view(), name='token_obtain_pair'),
    path('login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/verifyOTP', VerifyLoginOtpView.as_view(), name='token_obtain_pair'),
    path('auth/forgot', ForgotPasswordAPIView.as_view(), name='token_obtain_pair'),
    path('auth/forgot/OTP', ForgotOTPdAPIView.as_view(), name='forgot-otp'),
    path('auth/forgot/update/password', ForgotUpdatePasswordAPIView.as_view(), name='forgot-otp'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
]
# Transaction
urlpatterns += [
    path('api/transaction/', TransactionCreateAPIView.as_view(), name='purchase'),
    path('api/transaction/historiy/',TransactionsList.as_view())
]


urlpatterns += [
    path("api/analytics/", AnalyticsAPI.as_view(), name="analytics"),
]
from django.conf.urls.static import static
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView

from apps.views import ShopCreateAPIView, ShopListAPIView, CategoryCreatApi, CategoryListApi, CategoryUpdateApi, \
    CategoryDetailApi, UnitCreateApi, RoleCreateApi, RoleListApi, RoleDetailApi, RoleUpdateApi, ProductCreateApi, \
    ProductListApi, ProductDetailApi, ProductUpdateApi
from root import settings

urlpatterns = [
    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # SHOP
    path('api/shop/create/', ShopCreateAPIView.as_view()),
    path('api/shop/list/', ShopListAPIView.as_view()),

]
urlpatterns += [
    # Category
    path('api/category/create/', CategoryCreatApi.as_view()),
    path('api/category/list/', CategoryListApi.as_view()),
    path('categories/<str:id>/', CategoryDetailApi.as_view(), name='category-detail'),
    path('api/categories/<str:id>/update/', CategoryUpdateApi.as_view(), name='category-update'),
    # UNIT
    path('api/unit/creat/', UnitCreateApi.as_view()),

    # ROLE
    path('api/role/creat/', RoleCreateApi.as_view()),
    path('api/role/list/', RoleListApi.as_view()),
    path('api/role/<str:id>/delete/', RoleDetailApi.as_view()),
    path('api/role/<str:id>/update/', RoleUpdateApi.as_view()),
]

urlpatterns += [
                    #PRODUCTS
                   path('api/category/products/creat/', ProductCreateApi.as_view()),
    path('api/category/products/list/', ProductListApi.as_view()),
    path('api/category/products/<str:id>/delete/', ProductDetailApi.as_view()),
    path('api/category/products/<str:id>/update/', ProductUpdateApi.as_view()),

               ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

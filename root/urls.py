from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from root import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    # swagger-ui
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    #  swagger-ui:
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # apps.urls

    path('',include('apps.urls'))
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

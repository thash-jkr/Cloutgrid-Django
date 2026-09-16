from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("users.urls")),
    path("jobs/", include("jobs.urls")),
    path("posts/", include("feed.urls")),
    path("chats/", include("messaging.urls")),
    path('token/', 
        jwt_views.TokenObtainPairView.as_view(), 
        name ='token_obtain_pair'),
    path('token/refresh/', 
        jwt_views.TokenRefreshView.as_view(), 
        name ='token_refresh'),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

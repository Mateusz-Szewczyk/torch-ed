# torched/urls.py
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/', include('core.API.v1.urls')),  # Include other API routes from core app
    path('', include('core.urls'))
]

"""
URLs raiz do projeto.

Cada app expõe suas próprias rotas em seu próprio urls.py; aqui elas são
incluídas sob o prefixo /api/v1/. As rotas de autenticação JWT ficam neste
arquivo por serem transversais (não pertencem a um único app de negócio).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import CustomTokenObtainPairView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticação JWT
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='token_logout'),

    # Rotas de cada app de negócio
    path('api/v1/', include('accounts.urls')),
    path('api/v1/', include('barbershops.urls')),
    path('api/v1/', include('services.urls')),
    path('api/v1/', include('appointments.urls')),
]

# Em desenvolvimento, serve os arquivos de mídia (ex.: logo da barbearia)
# diretamente pelo Django. Em produção, isso deve ficar a cargo do
# servidor web (nginx, S3, etc.).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

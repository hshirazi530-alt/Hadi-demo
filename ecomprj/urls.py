"""ecomprj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.sitemaps.views import sitemap
from django.views.static import serve
from core.sitemaps import ProductSitemap, StorePagesSitemap
from core.views import robots_txt
from core.admin_dashboard import dashboard_view

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    re_path(r"^admin/$", admin.site.admin_view(dashboard_view), name="admin-dashboard"),
    path('admin/', admin.site.urls),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": {"products": ProductSitemap, "pages": StorePagesSitemap}},
        name="sitemap",
    ),
    path("robots.txt", robots_txt, name="robots-txt"),
    path("", include("core.urls")),
    path("user/", include("userauths.urls")),
    path("useradmin/", include("useradmin.urls")),

    # path("ckeditor/", include("ckeditor_uploader.urls")),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DJANGO_DEMO_SERVE_MEDIA:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
            name="demo-media",
        )
    ]
elif settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

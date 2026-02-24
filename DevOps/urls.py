"""
URL configuration for DevOps project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path, re_path, include
from dashboard import views
from django.conf.urls.static import static
from dashboard import views as dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path('^$',views.index),
    re_path('login',views.login),
    re_path('k8s/',include('k8s.urls')),
    re_path('workload/',include('workload.urls')),
    re_path('loadbalancer/',include('loadbalancer.urls')),
    re_path('storage/',include('storage.urls')),
    re_path('logout',views.logout),
    re_path('ace_editor/',views.ace_editor,name='ace_editor'),
    re_path('export_resource_api',views.export_resource_api,name='export_resource_api'),
    re_path('apply_yaml',views.apply_yaml,name='apply_yaml'),
    re_path('node_resource/$',views.node_resource,name='node_resource'),
    re_path('memory',views.memory,name='memory'),
    re_path('cpu',views.cpu,name='cpu'),
    path('io', views.io, name='io'),

]
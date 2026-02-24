
from django.urls import path, re_path, include
from k8s import views

urlpatterns = [
    re_path('home/$',views.home,name='home'),
    re_path('node/$',views.node,name='node'),
    re_path('pv/$',views.pv,name='pv'),
    re_path('pv_api/$',views.pv_api,name='pv_api'),
    re_path('namespace/$',views.namespace,name='namespace'),
    re_path('namespace_api/$',views.namespace_api,name='namespace_api'),
    re_path('node_api/$',views.node_api,name='node_api'), #$结尾防止匹配到node这个url
    re_path('pv_create/$',views.pv_create,name='pv_create'),
    re_path('node_details/$',views.node_detail,name='node_details'),
    re_path('deployment_details/$',views.deployment_details,name='deployment_details'),
    re_path('script/$',views.script, name='script'),
    re_path('script_api/$',views.script_api,name='script_api'),
]
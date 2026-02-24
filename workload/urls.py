from django.urls import path, re_path, include
from workload import views


urlpatterns = [
    re_path('deployment/$', views.deployment, name='deployment'),
    re_path('deployment_api/$', views.deployment_api, name='deployment_api'),
    re_path('daemonset/$',views.daemonset,name='daemonset'),
    re_path('daemonset_api/$',views.daemonset_api,name='daemonset_api'),
    re_path('pod/$',views.pod,name='pod'),
    re_path('pod_api/$',views.pod_api,name='pod_api'),
    re_path('^terminal/$', views.terminal, name="terminal"),
    re_path('logs/$',views.logs,name="logs"),
    re_path('statefulset/$',views.statefulset,name="statefulset"),
    re_path('statefulset_api/$',views.statefulset_api,name="statefulset_api"),
]
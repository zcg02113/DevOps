from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from django.urls import re_path
from DevOps.consumers import StreamConsumer
#告诉channels所有的http请求交给Django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DevOps.settings')
from django.core.asgi import get_asgi_application
from DevOps.logs_consumers import StreamLogConsumer


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            re_path(r'^workload/terminal/(?P<namespace>.*)/(?P<pod_name>.*)/(?P<container>.*)/', StreamConsumer.as_asgi()),
            re_path(r'^workload/pod_log/(?P<namespace>.*)/(?P<pod_name>.*)/(?P<container>.*)/', StreamLogConsumer.as_asgi()),
        ])
    ),
})
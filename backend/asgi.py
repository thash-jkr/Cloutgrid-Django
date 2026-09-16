"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messaging.routing import websocket_urlpatterns
from messaging.middleware import TokenAuthMiddleware

application = ProtocolTypeRouter({
    "http": asgi_app,
    "websocket": TokenAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    )
})

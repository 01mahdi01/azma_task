from django.urls import path
from .consumers import CommandConsumer

websocket_urlpatterns = [
    path("ws/commands/", CommandConsumer.as_asgi()),
]
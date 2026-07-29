from django.urls import re_path

from .consumer import VitalsConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/analytics/vitals/$",
        VitalsConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/analytics/residents/(?P<resident_id>\d+)/vitals/$",
        VitalsConsumer.as_asgi(),
    ),
]

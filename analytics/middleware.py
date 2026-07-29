from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _user_from_access_token(raw_token):
    try:
        token = AccessToken(raw_token)
        return get_user_model().objects.get(pk=token["user_id"])
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    """Authenticate a WebSocket using the existing SimpleJWT access token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        subprotocols = scope.get("subprotocols", [])

        try:
            marker_index = subprotocols.index("access-token")
            raw_token = subprotocols[marker_index + 1]
        except (ValueError, IndexError):
            raw_token = None

        if raw_token:
            scope["user"] = await _user_from_access_token(raw_token)
            scope["jwt_subprotocol"] = True

        return await self.app(scope, receive, send)

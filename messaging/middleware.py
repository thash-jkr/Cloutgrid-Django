from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user_from_token(raw_token):
    authenticator = JWTAuthentication()

    try:
        validated_token = authenticator.get_validated_token(raw_token)
        user = authenticator.get_user(validated_token)
        return user if user else AnonymousUser()
    except Exception:
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)

        raw_token = query_params.get("token", [None])[0]

        if raw_token:
            scope["user"] = await get_user_from_token(raw_token)
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
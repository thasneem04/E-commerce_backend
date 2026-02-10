from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    def get_raw_token(self, header):
        if header is None:
            return None
        # Prefer Authorization header if present
        raw = super().get_raw_token(header)
        if raw is not None:
            return raw
        return None

    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = self.get_raw_token(header)

        if raw_token is None:
            cookie_name = getattr(settings, "JWT_COOKIE_NAME", "access_token")
            raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError, AuthenticationFailed):
            # Ignore invalid/expired token for public endpoints
            return None
        user = self.get_user(validated_token)

        # If hitting seller APIs, let session auth handle seller users.
        if request.path.startswith("/api/seller/"):
            allowed_usernames = set(getattr(settings, "SELLER_USERNAMES", []))
            if not (
                user.is_staff
                or user.is_superuser
                or user.username in allowed_usernames
            ):
                return None

        return user, validated_token

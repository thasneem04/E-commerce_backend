from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # 1. Try Authorization header
        header = self.get_header(request)
        raw_token = None

        if header is not None:
            raw_token = self.get_raw_token(header)

        # 2. Fallback to cookie
        if raw_token is None:
            cookie_name = getattr(settings, "JWT_COOKIE_NAME", "access_token")
            raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            return None  # let SessionAuthentication try

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
        except (InvalidToken, TokenError):
            return None

        # ✅ IMPORTANT: return (user, None)
        return (user, None)

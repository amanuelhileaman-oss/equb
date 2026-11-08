from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from rest_framework.authentication import SessionAuthentication


class HybridSessionAuthentication(SessionAuthentication):
    """
    Dual-mode authentication for seamless cross-origin and same-origin support:
    1. Checks standard Django session cookies (with SameSite=None, Secure).
    2. Fallback to 'Authorization: Bearer <session_key>' or 'X-Session-ID: <session_key>'.
    
    This guarantees 100% reliable authentication across distinct subdomains
    (e.g., equb-frontend.onrender.com -> equb-backend-r9ie.onrender.com) even when
    browsers enforce strict third-party cookie blocking (Safari ITP, Chrome, Brave).
    """

    def authenticate(self, request):
        # 1. Attempt standard session cookie first
        user_auth = super().authenticate(request)
        if user_auth is not None:
            return user_auth

        # 2. Extract session key from Authorization header or X-Session-ID
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION', '')
        session_key = None
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() in ('bearer', 'session', 'token'):
                session_key = parts[1].strip()

        if not session_key:
            session_key = (request.headers.get('X-Session-ID') or request.META.get('HTTP_X_SESSION_ID', '')).strip()

        if not session_key:
            return None

        try:
            session = Session.objects.filter(session_key=session_key).first()
            if not session or session.expire_date < timezone.now():
                return None

            session_data = session.get_decoded()
            user_id = session_data.get('_auth_user_id')
            if not user_id:
                return None

            User = get_user_model()
            user = User.objects.filter(pk=user_id, is_active=True).first()
            if not user:
                return None

            return (user, None)
        except Exception:
            return None

    def enforce_csrf(self, request):
        # CSRF attacks only target ambient browser credentials (cookies).
        # When an explicit Authorization or X-Session-ID header is present,
        # cross-site request forgery is impossible, so CSRF check is bypassed for header auth.
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
        x_session = request.headers.get('X-Session-ID') or request.META.get('HTTP_X_SESSION_ID')
        if auth_header or x_session:
            return
        return super().enforce_csrf(request)


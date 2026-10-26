"""Middlewares de seguridad: login obligatorio, rate limit y cabeceras."""

from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

RATE_LIMITS = (
    ("/api/token/refresh/", 30, 60),
    ("/api/token/", 10, 60),
    ("/api/", 120, 60),
    ("/login/", 10, 60),
    ("/recuperar/", 5, 60),
)

PUBLIC_PREFIXES = (
    "/login/",
    "/logout/",
    "/recuperar/",
    "/terminos/",
    "/static/",
    "/admin/",
    "/api/",
    "/evidencias/",
    "/favicon.ico",
)

SIN_LIMITE = ("/static/", "/media/", "/admin/", "/favicon.ico")


class LoginRequiredMiddleware:
    """Ninguna página privada se sirve sin sesión iniciada."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        ruta = request.path_info
        if (
            usuario is not None
            and not usuario.is_authenticated
            and not any(ruta.startswith(exenta) for exenta in PUBLIC_PREFIXES)
        ):
            destino = reverse(settings.LOGIN_URL)
            return redirect(f"{destino}?next={quote(request.get_full_path(), safe='/')}")
        return self.get_response(request)


def _limite(ruta):
    for prefijo, limite, ventana in RATE_LIMITS:
        if ruta.startswith(prefijo):
            return prefijo, limite, ventana
    return "global", 300, 60


class RateLimitMiddleware:
    """Límite por IP con cache; se puede desactivar en pruebas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta = request.path_info
        if any(ruta.startswith(prefijo) for prefijo in SIN_LIMITE):
            return self.get_response(request)
        if getattr(settings, "TESTING", False) and not getattr(settings, "RATE_LIMIT_EN_PRUEBAS", False):
            return self.get_response(request)

        prefijo, limite, ventana = _limite(ruta)
        ip = request.META.get("REMOTE_ADDR") or "desconocida"
        # Ventana anclada al primer request (y no al minuto de reloj): así el
        # límite no se reinicia al cruzar un límite de minuto, que permitía
        # ráfagas dobles y hacía indeterminada esta parte de las pruebas.
        clave = f"rate:{prefijo}:{ip}"
        if cache.add(clave, 1, timeout=ventana):
            usado = 1
        else:
            try:
                usado = cache.incr(clave)
            except ValueError:
                cache.set(clave, 1, timeout=ventana)
                usado = 1
        if usado > limite:
            respuesta = JsonResponse(
                {"detalle": "Demasiadas solicitudes. Intenta más tarde."},
                status=429,
            ) if ruta.startswith("/api/") else HttpResponse(
                "Demasiadas solicitudes. Intenta más tarde.", status=429
            )
            respuesta["Retry-After"] = str(ventana)
            return respuesta
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """CSP y cabeceras de refuerzo para todas las respuestas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
            "form-action 'self'"
        )
        if getattr(settings, "CSP_REPORT_ONLY", False):
            respuesta["Content-Security-Policy-Report-Only"] = csp
        else:
            respuesta["Content-Security-Policy"] = csp
        respuesta.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.setdefault("Referrer-Policy", "same-origin")
        respuesta.setdefault("X-Frame-Options", "DENY")
        respuesta.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return respuesta

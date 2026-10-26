"""Tokens JWT de la API con datos útiles del usuario y segundo factor."""

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .permisos import rol_principal
from .seguridad import consumir_codigo_respaldo, perfil_de, verificar_totp


class KanviewTokenObtainPairSerializer(TokenObtainPairSerializer):
    otp = serializers.CharField(required=False, allow_blank=True, write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.get_username()
        token["email"] = user.email
        token["role"] = rol_principal(user)
        return token

    def validate(self, attrs):
        otp = (attrs.get("otp") or "").strip()
        data = super().validate(attrs)
        perfil = perfil_de(self.user)
        if perfil and perfil.totp_habilitado:
            valido = verificar_totp(perfil.totp_secret, otp) or consumir_codigo_respaldo(perfil, otp)
            if not valido:
                raise AuthenticationFailed("Se requiere un código 2FA válido.")
        return data


class KanviewTokenObtainPairView(TokenObtainPairView):
    serializer_class = KanviewTokenObtainPairSerializer

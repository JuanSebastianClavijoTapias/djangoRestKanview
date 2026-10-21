from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Autentica con el nombre de usuario o con el correo electrónico.

    La pantalla de login pide el correo, pero ``createsuperuser`` permite elegir
    un nombre de usuario distinto. Primero se intenta el comportamiento estándar
    y, si no hay coincidencia, se busca una única cuenta con ese correo.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        usuario = super().authenticate(
            request, username=username, password=password, **kwargs
        )
        if usuario is not None:
            return usuario
        if not username or not password or "@" not in username:
            return None

        UserModel = get_user_model()
        candidatos = list(
            UserModel._default_manager.filter(email__iexact=username)[:2]
        )
        if len(candidatos) != 1:
            return None

        candidato = candidatos[0]
        if candidato.check_password(password) and self.user_can_authenticate(candidato):
            return candidato
        return None

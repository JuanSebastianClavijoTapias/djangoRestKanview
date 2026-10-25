from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Autentica con usuario, correo o documento de un trabajador.

    El login del sitio pide un identificador; los clientes usan su correo y los
    trabajadores pueden usar el documento con el que fueron registrados.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        usuario = super().authenticate(
            request, username=username, password=password, **kwargs
        )
        if usuario is not None:
            return usuario
        if not username or not password:
            return None

        identificador = username.strip()
        UserModel = get_user_model()

        if "@" in identificador:
            candidatos = list(
                UserModel._default_manager.filter(email__iexact=identificador)[:2]
            )
            if len(candidatos) == 1:
                candidato = candidatos[0]
                if candidato.check_password(password) and self.user_can_authenticate(candidato):
                    return candidato
                return None

        # Documento del trabajador: se resuelve a su cuenta vinculada.
        from .models import Empleado

        empleados = list(
            Empleado.objects.filter(
                documento__iexact=identificador,
                activo=True,
                usuario__isnull=False,
            ).select_related("usuario")[:2]
        )
        if len(empleados) != 1:
            return None
        candidato = empleados[0].usuario
        if candidato.check_password(password) and self.user_can_authenticate(candidato):
            return candidato
        return None

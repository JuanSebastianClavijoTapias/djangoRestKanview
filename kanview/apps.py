from django.apps import AppConfig


class KanviewConfig(AppConfig):
    name = 'kanview'

    def ready(self):
        from . import checks  # noqa: F401  (registra las comprobaciones)

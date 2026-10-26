"""Consumer WebSocket del chat directo."""

import time
from collections import deque

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .mensajeria import (
    conversacion_visible,
    crear_mensaje,
    datos_mensaje,
    marcar_leidos,
)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    LIMITE_MENSAJES = 30
    VENTANA_SEGUNDOS = 10

    async def connect(self):
        self.usuario = self.scope.get("user")
        if not self.usuario or not self.usuario.is_authenticated:
            await self.close(code=4401)
            return
        self.conversacion_id = int(self.scope["url_route"]["kwargs"]["conversacion_id"])
        self.conversacion = await self._conversacion()
        if self.conversacion is None:
            await self.close(code=4403)
            return
        self.grupo = f"chat_{self.conversacion_id}"
        self._envios = deque()
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()
        await database_sync_to_async(marcar_leidos)(self.conversacion, self.usuario)
        await self.channel_layer.group_send(
            self.grupo,
            {"type": "chat.leidos", "usuario_id": self.usuario.pk},
        )

    async def disconnect(self, close_code):
        if hasattr(self, "grupo"):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("tipo") != "mensaje":
            return
        ahora = time.monotonic()
        while self._envios and ahora - self._envios[0] > self.VENTANA_SEGUNDOS:
            self._envios.popleft()
        if len(self._envios) >= self.LIMITE_MENSAJES:
            await self.send_json({
                "tipo": "error",
                "detalle": "Demasiados mensajes seguidos. Espera unos segundos.",
            })
            return
        self._envios.append(ahora)
        mensaje = await database_sync_to_async(crear_mensaje)(
            self.conversacion, self.usuario, content.get("texto")
        )
        if mensaje is None:
            return
        await self.channel_layer.group_send(
            self.grupo,
            {"type": "chat.message", "mensaje": datos_mensaje(mensaje)},
        )

    async def chat_message(self, event):
        if event["mensaje"]["autor_id"] != self.usuario.pk:
            await database_sync_to_async(marcar_leidos)(self.conversacion, self.usuario)
        await self.send_json({"tipo": "mensaje", "mensaje": event["mensaje"]})

    async def chat_leidos(self, event):
        await self.send_json({"tipo": "leidos", "usuario_id": event["usuario_id"]})

    @database_sync_to_async
    def _conversacion(self):
        return conversacion_visible(self.usuario, self.conversacion_id)

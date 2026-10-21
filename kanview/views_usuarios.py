"""Módulo Usuarios: clientes y trabajadores en dos columnas, con su cuenta de acceso.

Reglas acordadas (ver la especificación):

- Nadie se registra solo: el administrador (o Secretaría) crea la cuenta y le
  asigna un rol desde aquí.
- La cuenta es un ``User`` de Django con ``username = correo``.
- El vínculo persona ↔ cuenta es un campo explícito: ``Cliente.usuario`` /
  ``Empleado.usuario`` (``OneToOneField`` con ``PROTECT``). Antes se adivinaba
  por el correo o por una marca en ``User.last_name`` y eso permitía apropiarse
  de la cuenta de otra persona; ahora ``usuario_acceso`` escribe SOLO ese campo.
- Tanto ``Cliente`` como ``Empleado`` tienen su propio campo ``correo``.

Vistas: lista, ver, crear/actualizar acceso y activar/desactivar la cuenta.
"""

import secrets
import string

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .auditoria import registrar as registrar_auditoria
from .models import Cliente, Empleado, Pedido, TareasPedido
from .permisos import (
    ROL_CLIENTE,
    ROL_TRABAJADOR,
    ROLES,
    asignar_rol,
    rol_principal,
    seccion_requerida,
)
from .views_site import _nav

# ---- Vínculo persona <-> cuenta -------------------------------------------


def _obtener(tipo, pk):
    """Devuelve ``(persona, etiqueta)`` según el tipo de usuario."""
    if tipo == "cliente":
        return get_object_or_404(Cliente, pk=pk), "Cliente"
    if tipo == "trabajador":
        return get_object_or_404(Empleado, pk=pk), "Trabajador"
    raise Http404("Tipo de usuario desconocido.")


def _usuario_de(tipo, persona):
    """Cuenta de acceso de la persona, o ``None`` si todavía no tiene."""
    return persona.usuario


def _correo_sugerido(tipo, persona):
    """Correo con el que se creará la cuenta cuando la persona no trae uno.

    Los trabajadores suelen no tener correo propio: se deriva uno interno a
    partir del documento. En los clientes el correo es real y, si falta, se
    agrega desde «Editar» antes de crear la cuenta.
    """
    if tipo != "trabajador":
        return ""
    base = (persona.documento or "").strip().lower().replace(" ", "")
    if not base:
        base = f"trabajador{persona.pk}"
    return f"{base}@kanview.local"


def _clave_temporal():
    """Contraseña temporal legible para una cuenta recién creada."""
    return "Kanview" + "".join(secrets.choice(string.digits) for _ in range(4)) + "!"


def _correo_de(tipo, persona, user):
    if user is not None:
        return user.email or user.username
    return (getattr(persona, "correo", "") or "").strip() or _correo_sugerido(tipo, persona)


def _fila_persona(tipo, persona):
    """Fila de la tabla de usuarios (clientes o trabajadores)."""
    user = _usuario_de(tipo, persona)
    tiene_acceso = user is not None
    activo = user.is_active if user is not None else bool(persona.activo)
    url_editar = "kanview:cliente-editar" if tipo == "cliente" else "kanview:empleado-editar"
    return {
        "pk": persona.pk,
        "nombre": persona.nombre,
        "documento": persona.documento,
        "contacto": getattr(persona, "celular", ""),
        "correo": _correo_de(tipo, persona, user),
        "estado": "Activo" if activo else "Inactivo",
        "estado_clase": "bg-[#006565]/10 text-[#006565]" if activo else "bg-gray-200 text-gray-600",
        "tiene_acceso": tiene_acceso,
        "rol": rol_principal(user) if tiene_acceso else "",
        "ver_url": reverse("kanview:usuario-ver", args=[tipo, persona.pk]),
        "editar_url": reverse(url_editar, args=[persona.pk]),
        "acceso_url": reverse("kanview:usuario-acceso", args=[tipo, persona.pk]),
        "estado_url": reverse("kanview:usuario-estado", args=[tipo, persona.pk]),
    }


# ---- Vistas ---------------------------------------------------------------


@seccion_requerida("usuarios")
def usuarios(request):
    """Clientes y trabajadores en dos columnas, cada una con su botón Nuevo.

    Se muestran todos (activos e inactivos) porque es la pantalla desde la que
    se activa y desactiva cada cuenta: el estado va en su píldora.
    """
    clientes = list(Cliente.objects.all().order_by("-id"))
    trabajadores = list(Empleado.objects.all().order_by("-id"))
    contexto = {
        "filas_clientes": [_fila_persona("cliente", c) for c in clientes],
        "filas_trabajadores": [_fila_persona("trabajador", e) for e in trabajadores],
        "crear_cliente_url": reverse("kanview:cliente-crear"),
        "crear_trabajador_url": reverse("kanview:empleado-crear"),
        "roles": ROLES,
        "total_clientes": len(clientes),
        "total_trabajadores": len(trabajadores),
        "cabecera_titulo": "Usuarios",
        **_nav("Usuarios", request),
    }
    return render(request, "kanview/usuarios.html", contexto)


@seccion_requerida("usuarios")
def usuario_ver(request, tipo, pk):
    """Ficha de un cliente o trabajador con sus datos, cuenta y relacionados."""
    persona, etiqueta = _obtener(tipo, pk)
    user = _usuario_de(tipo, persona)

    if tipo == "cliente":
        datos = [
            {"etiqueta": "Nombre", "valor": persona.nombre},
            {"etiqueta": "Documento", "valor": persona.documento or "—"},
            {"etiqueta": "Celular", "valor": persona.celular or "—"},
            {"etiqueta": "Dirección", "valor": persona.direccion or "—"},
            {"etiqueta": "Fecha de nacimiento", "valor": persona.fecha_nacimiento or "—"},
            {"etiqueta": "Edad", "valor": persona.edad},
            {"etiqueta": "Correo", "valor": persona.correo or "—"},
        ]
        pedidos = Pedido.objects.filter(id_cliente=persona).order_by("-id")
        relacionados = [{
            "titulo": "Pedidos del cliente",
            "filas": [
                f"{p.codigo_pedido} · {p.get_estado_display()} · {p.fecha_creacion:%d/%m/%Y}"
                for p in pedidos
            ],
        }]
    else:
        datos = [
            {"etiqueta": "Nombre", "valor": persona.nombre},
            {"etiqueta": "Documento", "valor": persona.documento or "—"},
            {"etiqueta": "Cargo", "valor": persona.get_cargo_display()},
            {"etiqueta": "Celular", "valor": persona.celular or "—"},
            {"etiqueta": "Dirección", "valor": persona.direccion or "—"},
            {"etiqueta": "Salario", "valor": persona.salario},
            {"etiqueta": "Tareas realizadas", "valor": persona.tareas_realizadas},
            {"etiqueta": "Fecha de nacimiento", "valor": persona.fecha_nacimiento or "—"},
            {"etiqueta": "Edad", "valor": persona.edad},
            {"etiqueta": "Correo", "valor": persona.correo or "—"},
        ]
        tareas = TareasPedido.objects.filter(id_pedido__id_empleado=persona).order_by("-id")
        relacionados = [{
            "titulo": "Tareas asignadas",
            "filas": [
                f"{t.nombre} · {t.get_estado_display()} · {t.fecha_fin:%d/%m/%Y}"
                for t in tareas
            ],
        }]

    contexto = {
        "tipo": tipo,
        "titulo": f"{etiqueta}: {persona.nombre}",
        "persona": persona,
        "datos": datos,
        "correo": _correo_de(tipo, persona, user),
        "rol": rol_principal(user) if user is not None else "",
        "activo": user.is_active if user is not None else bool(persona.activo),
        "tiene_acceso": user is not None,
        "acceso_url": reverse("kanview:usuario-acceso", args=[tipo, pk]),
        "estado_url": reverse("kanview:usuario-estado", args=[tipo, pk]),
        "volver_url": reverse("kanview:usuarios"),
        "relacionados": relacionados,
        "roles": ROLES,
        "cabecera_titulo": f"{etiqueta}: {persona.nombre}",
        **_nav("Usuarios", request),
    }
    return render(request, "kanview/usuarios_detalle.html", contexto)


@seccion_requerida("usuarios")
def usuario_acceso(request, tipo, pk):
    """Crea o actualiza la cuenta (username=correo) y su rol. Solo POST.

    Solo escribe ``persona.usuario``: nunca reutiliza ni reescribe la cuenta de
    otra persona (si el correo ya pertenece a otra cuenta, avisa y no toca nada).
    """
    persona, etiqueta = _obtener(tipo, pk)
    destino = reverse("kanview:usuario-ver", args=[tipo, pk])
    if request.method != "POST":
        return redirect(destino)

    correo = (
        (request.POST.get("correo") or "").strip().lower()
        or (getattr(persona, "correo", "") or "").strip().lower()
        or _correo_sugerido(tipo, persona)
    )
    clave = request.POST.get("clave") or ""
    rol = request.POST.get("rol") or (ROL_CLIENTE if tipo == "cliente" else ROL_TRABAJADOR)
    if rol not in ROLES:
        rol = ROL_CLIENTE if tipo == "cliente" else ROL_TRABAJADOR

    if not correo or "@" not in correo:
        messages.error(request, "Necesitas un correo válido para dar acceso.")
        return redirect(destino)

    if clave and len(clave) < 8:
        messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
        return redirect(destino)

    user = _usuario_de(tipo, persona)
    # El correo no puede pertenecer a otra cuenta: eso era justo lo que permitía
    # apropiarse de la cuenta de alguien más.
    existente = User.objects.filter(Q(username__iexact=correo) | Q(email__iexact=correo)).first()
    if existente is not None and (user is None or existente.pk != user.pk):
        messages.error(request, f"El correo {correo} ya pertenece a otra cuenta.")
        return redirect(destino)

    creada = user is None
    clave_temporal = ""
    if creada:
        if not clave:
            clave_temporal = _clave_temporal()
            clave = clave_temporal
        user = User(username=correo)

    if clave:
        user.set_password(clave)
    user.username = correo
    user.email = correo
    user.first_name = persona.nombre[:150]
    user.is_active = True
    user.save()

    persona.usuario = user
    campos_persona = ["usuario"]
    if (getattr(persona, "correo", "") or "").lower() != correo:
        persona.correo = correo
        campos_persona.append("correo")
    persona.save(update_fields=campos_persona)

    asignar_rol(user, rol)

    verbo = "creada" if creada else "actualizada"
    registrar_auditoria(
        request, "acceso", "Usuario", user,
        f"Cuenta de {persona.nombre} {verbo} con rol {rol}.",
    )
    messages.success(request, f"Cuenta de {persona.nombre} {verbo} con rol {rol}.")
    if clave_temporal:
        messages.warning(
            request,
            f"Contraseña temporal de {correo}: {clave_temporal}. Cámbiala al primer ingreso.",
        )
    return redirect(destino)


@seccion_requerida("usuarios")
def usuario_estado(request, tipo, pk):
    """Activa o desactiva la cuenta (o el registro si aún no tiene cuenta). Solo POST."""
    persona, etiqueta = _obtener(tipo, pk)
    if request.method != "POST":
        return redirect(reverse("kanview:usuario-ver", args=[tipo, pk]))

    user = _usuario_de(tipo, persona)
    if user is not None:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        estado = "activada" if user.is_active else "desactivada"
        registrar_auditoria(
            request, "estado_cuenta", "Usuario", user,
            f"Cuenta {estado}: {persona.nombre}",
        )
        messages.success(request, f"Cuenta de {persona.nombre} {estado}.")
    else:
        persona.activo = not persona.activo
        persona.save(update_fields=["activo"])
        estado = "activado" if persona.activo else "desactivado"
        messages.success(
            request,
            f"{etiqueta} {persona.nombre} {estado} (todavía no tiene cuenta de acceso).",
        )
    return redirect("kanview:usuarios")

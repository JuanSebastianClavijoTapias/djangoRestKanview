"""Consulta del log de auditoría y gestión de copias de seguridad."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .auditoria import registrar as registrar_auditoria
from .models import RegistroAuditoria
from .permisos import es_administrador, seccion_requerida
from .respaldos import crear_respaldo, listar_respaldos, restaurar_respaldo
from .views_site import _nav

POR_PAGINA = 25


@seccion_requerida("auditoria")
def auditoria_log(request):
    q = (request.GET.get("q") or "").strip()
    accion = (request.GET.get("accion") or "").strip()
    consulta = RegistroAuditoria.objects.select_related("usuario").order_by("-fecha_creacion", "-id")
    if q:
        consulta = consulta.filter(
            Q(descripcion__icontains=q)
            | Q(entidad__icontains=q)
            | Q(usuario__username__icontains=q)
            | Q(usuario__first_name__icontains=q)
        )
    if accion:
        consulta = consulta.filter(accion=accion)
    paginator = Paginator(consulta, POR_PAGINA)
    pagina = paginator.get_page(request.GET.get("page"))
    acciones = (
        RegistroAuditoria.objects.values_list("accion", flat=True).distinct().order_by("accion")
    )
    return render(
        request,
        "kanview/auditoria_log.html",
        {
            "page_obj": pagina,
            "registros": pagina.object_list,
            "paginator": paginator,
            "acciones": acciones,
            "accion_activa": accion,
            "q": q,
            "total": paginator.count,
            **_nav("Auditoría", request),
        },
    )


@seccion_requerida("configuracion")
def respaldos(request):
    if not es_administrador(request.user):
        messages.error(request, "Solo Administración puede gestionar las copias de seguridad.")
        return redirect("kanview:configuracion")
    return render(
        request,
        "kanview/respaldos.html",
        {"respaldos": listar_respaldos(), **_nav("Configuración", request)},
    )


@seccion_requerida("configuracion")
@require_POST
def respaldos_crear(request):
    if not es_administrador(request.user):
        messages.error(request, "Solo Administración puede crear copias de seguridad.")
        return redirect("kanview:configuracion")
    try:
        ruta = crear_respaldo()
        registrar_auditoria(
            request, "backup", "BaseDatos", objeto_id=ruta.name,
            descripcion=f"Copia de seguridad creada: {ruta.name}",
        )
        messages.success(request, f"Copia creada: {ruta.name}")
    except Exception as error:
        messages.error(request, f"No se pudo crear la copia: {error}")
    return redirect("kanview:respaldos")


@seccion_requerida("configuracion")
@require_POST
def respaldos_restaurar(request):
    if not es_administrador(request.user):
        messages.error(request, "Solo Administración puede restaurar copias de seguridad.")
        return redirect("kanview:configuracion")
    nombre = (request.POST.get("nombre") or "").strip()
    if not nombre:
        messages.error(request, "Selecciona una copia de seguridad.")
        return redirect("kanview:respaldos")
    try:
        seguridad = restaurar_respaldo(nombre)
        registrar_auditoria(
            request, "restaurar", "BaseDatos", objeto_id=nombre,
            descripcion=f"Base restaurada desde {nombre}. Seguridad previa: {seguridad.name}",
        )
        messages.success(
            request,
            f"Base restaurada desde {nombre}. Se guardó una copia previa: {seguridad.name}.",
        )
    except Exception as error:
        messages.error(request, f"No se pudo restaurar: {error}")
    return redirect("kanview:respaldos")

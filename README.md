# Kanview

Sistema de gestión para Cuir Tapicería (taller de tapicería en cuero): API con Django REST Framework (vistas basadas en funciones) más un conjunto de páginas de interfaz (Django templates).

## Requisitos

- Python 3.12 o superior
- pip

## Instalación

```bash
git clone <url-del-repo>
cd djangoRestKanview

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Base de datos

El proyecto usa SQLite por defecto (no requiere instalar nada aparte). Aplica las migraciones:

```bash
python3 manage.py migrate
```

Dependencias nuevas para PDF y 2FA: `reportlab`, `pyotp` y `qrcode` (incluidas en `requirements.txt`).

La factura se genera en PDF y se envía por correo desde el detalle del pedido. Las copias de seguridad se guardan en `backups/` (configurable con `BACKUP_DIR`) y solo las gestiona Administración.

El rol Cliente ve el catálogo (`/catalogo/`) y crea sus propios pedidos desde él (`/pedidos/nuevo/`): elige producto y cantidad, y el pedido queda «Pendiente de aprobación» sin trabajador asignado. Al aprobarlo, el taller le asigna el trabajador responsable. Cada pedido descuenta el stock del producto; desactivar un pedido lo devuelve.

El chat usa Django Channels y WebSockets. `runserver` funciona con Daphne; en desarrollo se usa un canal en memoria. Para producción con varios procesos configura `CHANNEL_LAYERS` con `channels_redis`.

## Seguridad

- La API acepta JWT: `POST /api/token/`, `POST /api/token/refresh/` y `POST /api/token/blacklist/`. Si la cuenta tiene 2FA, `/api/token/` exige el campo `otp`.
- Las páginas privadas exigen sesión; login, recuperación, términos y evidencias firmadas son públicos.
- Rate limit por IP para login, recuperación, API y tráfico general.
- Cabeceras CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy` y `Permissions-Policy`.
- CSRF obligatorio en formularios web; cookies de sesión/CSRF con `HttpOnly` y `SameSite=Lax`.
- Variables útiles: `CSRF_TRUSTED_ORIGINS`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` y `CSP_REPORT_ONLY`.
- Para varias instancias, configura `CACHE_BACKEND`/`CACHE_LOCATION` con un cache compartido; el rate limit en memoria solo protege un proceso.
- La CSP permite scripts inline porque la interfaz actual los usa; al migrarlos a archivos estáticos se puede endurecer con nonces y quitar `'unsafe-inline'`.

Variables de entorno útiles: `EMPRESA_NOMBRE`, `EMPRESA_NIT`, `EMPRESA_DIRECCION`, `EMPRESA_TELEFONO`, `EMPRESA_CORREO`, `FACTURA_IVA`, `TERMINOS_VERSION`, `BACKUP_DIR`, `BACKUP_RETENCION`, `MAX_VIDEO_BYTES` y `MAX_BYTES_MULTIMEDIA`. El archivo `.env.example` documenta todas las variables.

### Correo

El envío de correos (recuperación de contraseña, facturas, evidencias) usa SMTP y se configura por entorno: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` y `DEFAULT_FROM_EMAIL`. Sin credenciales SMTP el envío falla y se registra en el log. Para desarrollo, `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` imprime los correos en la terminal.

Opcional, para poder entrar a `/admin/`:

```bash
python3 manage.py createsuperuser
```

## Levantar el servidor

```bash
python3 manage.py runserver
```

Por defecto queda disponible en `http://127.0.0.1:8000/`. Si ese puerto está ocupado:

```bash
python3 manage.py runserver 8010
```

## Despliegue

La guía para publicar el sistema en Render está en
[DESPLIEGUE_RENDER.md](DESPLIEGUE_RENDER.md).

## Rutas

### API (Django REST Framework)

Todas bajo el prefijo `/api/`. Cada recurso tiene una ruta de lista (`GET` para listar,
`POST` para crear) y una de detalle (`GET`, `PUT` y `DELETE` sobre un registro):

```
/api/clientes/                 /api/clientes/<id>/
/api/empleados/                /api/empleados/<id>/
/api/administradores/          /api/administradores/<id>/
/api/analisis-financieros/     /api/analisis-financieros/<id>/
/api/productos/                /api/productos/<id>/
/api/inventarios/              /api/inventarios/<id>/
/api/catalogos/                /api/catalogos/<id>/
/api/pedidos/                  /api/pedidos/<id>/
/api/tareas-pedido/            /api/tareas-pedido/<id>/
/api/actividades/              /api/actividades/<id>/
/api/historial/                /api/historial/<id>/
/api/calendario/               /api/calendario/<id>/
```

### Interfaz (páginas)

```
/                  Tablero de pedidos (home)
/login/            Inicio de sesión
/logout/           Cerrar sesión
/pedidos/          Tablero de pedidos
/pedidos/<id>/     Detalle del pedido (aprobación, multimedia, factura e historial)
/tareas/           Listado y gestión de tareas
/tareas/<id>/      Detalle y confirmación de una tarea
/actividades/      Tablero de actividades con filtros por área
/calendario/       Calendario de producción
/inventario/       Inventario de materiales
/finanzas/         Análisis financiero
/auditoria/        Historial de pedidos
/auditoria/log/    Log de acciones del sistema
/mensajeria/       Chat interno en tiempo real
/perfil/           Perfil, contraseña y 2FA
/terminos/         Términos y condiciones
/configuracion/backups/  Copias de seguridad (solo Administración)
/clientes/         Gestión de clientes
/empleados/        Gestión de empleados
/catalogo/         Catálogo de productos
/admin/            Panel de administración de Django
```

### CRUD (formularios de la interfaz)

Cada recurso tiene listar, crear, editar y eliminar:

```
/crud/clientes/    /crud/clientes/nuevo/    /crud/clientes/<id>/editar/    /crud/clientes/<id>/eliminar/
/crud/empleados/   ...
/crud/administradores/
/crud/productos/
/crud/pedidos/
/crud/inventario/
/crud/calendario/
/crud/tareas/
/crud/actividades/
/crud/catalogo/
/crud/historial/
```

### CRUD (formularios de alta/baja/edición)

Páginas de gestión reales (listar, crear, editar y eliminar) bajo el prefijo `/crud/`. Cubren los 12 modelos del sistema:

```
/crud/clientes/             /crud/empleados/          /crud/administradores/
/crud/productos/            /crud/pedidos/
/crud/analisis-financieros/ /crud/inventarios/        /crud/catalogos/
/crud/tareas/               /crud/actividades/
/crud/historial/            /crud/calendario/
```

Cada sección expone: `/crud/<seccion>/` (lista), `/nuevo/` (crear), `/<id>/editar/` y `/<id>/eliminar/`.

## Estructura del proyecto

```
config/     Configuración del proyecto Django (settings, urls raíz)
kanview/    App principal:
            models.py       Modelos de la base de datos
            serializers.py  Serializers de DRF
            views.py        Vistas de la API (@api_view, basadas en funciones)
            urls.py         Rutas de la API
            views_site.py   Vistas de las páginas (basadas en funciones)
            views_crud.py   Vistas del CRUD (basadas en funciones)
            urls_site.py    Rutas de las páginas y del CRUD
            views_crud.py   Formularios construidos con modelform_factory
            templates/      Plantillas HTML
```

> Nota: las páginas de diseño (las que no son CRUD) muestran datos de ejemplo fijos en el HTML; todavía no están conectadas a los datos reales de la API (`/api/...`).

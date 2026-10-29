# Despliegue de Kanview en Render

Esta guía usa el formulario de **New Web Service** de Render y los cambios de
producción ya incorporados al proyecto: WhiteNoise para archivos estáticos,
soporte para base de datos y media en un disco persistente, y detección del
hostname de Render.

## Campos del formulario

| Campo | Valor |
|---|---|
| **Region** | `Virginia (US East)` |
| **Root Directory** | Déjalo vacío. |
| **Build Command** | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| **Start Command** | `python manage.py migrate --noinput && python -m daphne -b 0.0.0.0 -p $PORT config.asgi:application` |
| **Compute** | `$7 / month · 0.5 CPU · 512 MB RAM` o superior. |
| **Health Check Path** | `/login/` si Render lo solicita. |
| **Auto-Deploy** | Activado. |

No uses el plan gratuito para datos reales. El plan gratuito no ofrece disco
persistente y el servicio puede suspenderse; con SQLite se perderían la base de
datos, las evidencias y los respaldos en cada reinicio o despliegue.

## Disco persistente

El disco se puede agregar de dos formas:

- Durante la creación del servicio: abre **Advanced**, al final del formulario, y agrega el disco.
- Después de crear el servicio: entra al servicio, abre la página **Disk** y pulsa **Add disk**.

| Campo | Valor |
|---|---|
| **Name** | `kanview-data` |
| **Mount Path** | `/var/data` |
| **Size** | `1 GB` mínimo; `5 GB` o más si se cargarán videos. |

El disco debe existir antes de iniciar el servicio con las rutas configuradas.
Render solo conserva los archivos que estén dentro de `/var/data`; el resto del
sistema de archivos es efímero.

Después de guardar el disco, Render hace un nuevo deploy. El disco solo está
disponible en tiempo de ejecución, no durante el Build Command. Por eso las
migraciones se ejecutan en el Start Command, cuando el disco ya está montado.

El disco persistente limita el servicio a una sola instancia y hace que los
deploys tengan una breve interrupción. Para este proyecto es aceptable porque
SQLite no debe compartirse entre varias instancias.

## Variables de entorno

En **Environment > Environment Variables**, agrega:

```env
SECRET_KEY=genera-una-clave-larga-y-unica
DEBUG=False
ALLOWED_HOSTS=tu-servicio.onrender.com
CSRF_TRUSTED_ORIGINS=https://tu-servicio.onrender.com

DATABASE_PATH=/var/data/db.sqlite3
MEDIA_ROOT=/var/data/media
BACKUP_DIR=/var/data/backups

CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSP_REPORT_ONLY=False

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=tu-correo@gmail.com
EMAIL_HOST_PASSWORD=tu-contrasena-de-aplicacion
DEFAULT_FROM_EMAIL=tu-correo@gmail.com

CORREO_CONTACTO=contacto@kanview.com
EMPRESA_NOMBRE=Kanview · Cuir Tapicería
EMPRESA_NIT=000.000.000-0
EMPRESA_DIRECCION=Dirección del taller
EMPRESA_TELEFONO=000 000 0000
EMPRESA_CORREO=contacto@kanview.com
FACTURA_IVA=0
TERMINOS_VERSION=1.0
```

Reemplaza `tu-servicio.onrender.com` por el dominio real que Render asigne al
servicio. Si usas un dominio propio, agrégalo también a `ALLOWED_HOSTS` y a
`CSRF_TRUSTED_ORIGINS` con su esquema HTTPS.

Para generar la `SECRET_KEY` localmente:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Si todavía no tienes SMTP, para la primera prueba puedes usar:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Después configura el SMTP real para recuperación de contraseñas, facturas y
notificaciones.

## Crear el administrador

Después del primer despliegue, abre la **Shell** de Render y ejecuta:

```bash
python manage.py createsuperuser
```

## Verificación

Comprueba que el servicio responde en:

```text
https://tu-servicio.onrender.com/login/
```

Luego verifica:

- El panel de administración en `/admin/` carga con estilos.
- Se puede iniciar sesión.
- Se puede crear un cliente y un pedido de prueba.
- Las evidencias se guardan y se pueden abrir.
- La campana y la mensajería funcionan.
- Se puede crear una copia de seguridad desde Configuración > Respaldos.
- El disco persistente conserva los datos después de un redeploy.

## WebSockets y escalado

La configuración actual usa `InMemoryChannelLayer`, válida para **una sola
instancia**. Con el plan de 0.5 CPU/512 MB hay una instancia, por lo que la
mensajería en tiempo real funciona.

Si más adelante escalas a varias instancias:

- Instala `channels-redis`.
- Configura Redis y `CHANNEL_LAYERS` en `config/settings.py`.
- Configura un cache compartido (`django-redis`) para el rate limit.
- No uses SQLite compartido entre varias instancias.

## Respaldos

La base de datos, las evidencias y los respaldos viven en `/var/data`. Aun así,
descarga periódicamente una copia fuera de Render; un disco persistente no
sustituye un respaldo externo.

## Solución de problemas

- **`DisallowedHost`**: revisa `ALLOWED_HOSTS`; la configuración ya agrega
  automáticamente `RENDER_EXTERNAL_HOSTNAME`.
- **Error CSRF**: revisa que `CSRF_TRUSTED_ORIGINS` incluya el dominio con
  `https://`.
- **No se ven estilos del admin**: confirma que el Build Command ejecutó
  `collectstatic`.
- **La base se reinicia o se pierde**: verifica que el disco esté montado en
  `/var/data` y que `DATABASE_PATH` apunte allí.
- **WebSocket desconectado**: confirma que estás usando el plan pagado, una sola
  instancia y el Start Command con Daphne.
- **Error 429**: es el rate limit; espera la ventana correspondiente.
- **Correos no enviados**: revisa las credenciales SMTP y reinicia el servicio.

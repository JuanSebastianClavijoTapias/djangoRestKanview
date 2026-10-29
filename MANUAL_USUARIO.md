# Manual de usuario · Instalación y puesta en marcha

Esta sección describe cómo instalar Kanview, preparar su entorno, configurar la
base de datos y levantar el servidor. Está pensada para el administrador técnico
del sistema.

## 1. Requisitos

- **Python 3.12 o superior**.
- `pip` y el módulo `venv` de Python.
- Git, solo si vas a clonar el proyecto desde un repositorio.
- Un navegador moderno: Chrome, Edge, Firefox o Safari.
- **SQLite**, que viene incluido con Python; no hay que instalar un motor de base
  de datos aparte.
- Conexión a un servidor SMTP para recuperación de contraseña, envío de facturas
  y notificaciones por correo. Sin SMTP el sistema funciona, pero esos correos no
  se envían.
- Opcional: Node.js y npm para ejecutar las pruebas E2E con Cypress.
- Opcional para producción con varias instancias: Redis, `channels-redis` y
  `django-redis`.

En Ubuntu/Debian, si falta el entorno virtual:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

## 2. Dependencias del proyecto

Las dependencias de Python están fijadas en `requirements.txt`:

| Dependencia | Uso |
|---|---|
| `Django==6.1` | Framework principal. |
| `djangorestframework==3.18.0` | API REST. |
| `djangorestframework-simplejwt==5.5.1` | Tokens JWT para la API. |
| `channels==4.3.2` | WebSockets de la mensajería. |
| `daphne==4.2.3` | Servidor ASGI para HTTP y WebSockets. |
| `asgiref==3.12.1` | Soporte ASGI usado por Django y Channels. |
| `Pillow==13.0.0` | Validación y procesamiento de imágenes. |
| `reportlab==5.0.1` | Generación de facturas PDF. |
| `pyotp==2.10.0` | Códigos TOTP para 2FA. |
| `qrcode==8.2` | Código QR para activar 2FA. |
| `python-dotenv==1.2.4` | Carga del archivo `.env`. |
| `sqlparse==0.6.0` | Dependencia de Django para SQL. |

Instalación:

```bash
pip install -r requirements.txt
```

Si `pip` intenta compilar `Pillow` en Linux y falla, instala las librerías del
sistema necesarias para JPEG/PNG. Normalmente las ruedas precompiladas evitan
este paso.

Dependencias opcionales:

```bash
# Pruebas E2E con Cypress
npm install

# Producción con varias instancias y Redis
pip install channels-redis django-redis
```

No es necesario instalar Node ni Redis para ejecutar el sistema en desarrollo.

## 3. Preparar el entorno

Clona el repositorio si aún no lo tienes:

```bash
git clone https://github.com/JuanSebastianClavijoTapias/djangoRestKanview.git
cd djangoRestKanview
```

Crea y activa el entorno virtual:

```bash
python3 -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows PowerShell
# .\venv\Scripts\Activate.ps1
```

Actualiza `pip` e instala las dependencias:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verifica la instalación:

```bash
python -c "import django; print(django.get_version())"
python manage.py check
```

## 4. Configurar las variables de entorno

Crea el archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

Edita `.env` con los datos reales del taller. Como mínimo, para desarrollo:
# Manual de usuario · Instalación y puesta en marcha

Esta sección describe cómo instalar Kanview, preparar su entorno, configurar la
base de datos y levantar el servidor. Está pensada para el administrador técnico
del sistema.

## 1. Requisitos

- **Python 3.12 o superior**.
- `pip` y el módulo `venv` de Python.
- Git, solo si vas a clonar el proyecto desde un repositorio.
- Un navegador moderno: Chrome, Edge, Firefox o Safari.
- **SQLite**, que viene incluido con Python; no hay que instalar un motor de base
  de datos aparte.
- Conexión a un servidor SMTP para recuperación de contraseña, envío de facturas
  y notificaciones por correo. Sin SMTP el sistema funciona, pero esos correos no
  se envían.
- Opcional: Node.js y npm para ejecutar las pruebas E2E con Cypress.
- Opcional para producción con varias instancias: Redis, `channels-redis` y
  `django-redis`.

En Ubuntu/Debian, si falta el entorno virtual:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

## 2. Dependencias del proyecto

Las dependencias de Python están fijadas en `requirements.txt`:

| Dependencia | Uso |
|---|---|
| `Django==6.1` | Framework principal. |
| `djangorestframework==3.18.0` | API REST. |
| `djangorestframework-simplejwt==5.5.1` | Tokens JWT para la API. |
| `channels==4.3.2` | WebSockets de la mensajería. |
| `daphne==4.2.3` | Servidor ASGI para HTTP y WebSockets. |
| `asgiref==3.12.1` | Soporte ASGI usado por Django y Channels. |
| `Pillow==13.0.0` | Validación y procesamiento de imágenes. |
| `reportlab==5.0.1` | Generación de facturas PDF. |
| `pyotp==2.10.0` | Códigos TOTP para 2FA. |
| `qrcode==8.2` | Código QR para activar 2FA. |
| `python-dotenv==1.2.4` | Carga del archivo `.env`. |
| `sqlparse==0.6.0` | Dependencia de Django para SQL. |

Instalación:

```bash
pip install -r requirements.txt
```

Si `pip` intenta compilar `Pillow` en Linux y falla, instala las librerías del
sistema necesarias para JPEG/PNG. Normalmente las ruedas precompiladas evitan
este paso.

Dependencias opcionales:

```bash
# Pruebas E2E con Cypress
npm install

# Producción con varias instancias y Redis
pip install channels-redis django-redis
```

No es necesario instalar Node ni Redis para ejecutar el sistema en desarrollo.

## 3. Preparar el entorno

Clona el repositorio si aún no lo tienes:

```bash
git clone https://github.com/JuanSebastianClavijoTapias/djangoRestKanview.git
cd djangoRestKanview
```

Crea y activa el entorno virtual:

```bash
python3 -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows PowerShell
# .\venv\Scripts\Activate.ps1
```

Actualiza `pip` e instala las dependencias:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verifica la instalación:

```bash
python -c "import django; print(django.get_version())"
python manage.py check
```

## 4. Configurar las variables de entorno

Crea el archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

Edita `.env` con los datos reales del taller. Como mínimo, para desarrollo:

```env
SECRET_KEY=una-clave-secreta-larga-y-única
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Para generar una `SECRET_KEY` segura:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Variables principales

| Variable | Ejemplo | Uso |
|---|---|---|
| `SECRET_KEY` | cadena larga y aleatoria | Firma de sesiones, tokens y enlaces. Obligatoria en producción. |
| `DEBUG` | `True` en desarrollo | Activa el modo de depuración. En producción debe ser `False`. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Dominios o IPs desde los que se accede al sistema. |
| `EMAIL_HOST` | `smtp.gmail.com` | Servidor SMTP. |
| `EMAIL_PORT` | `587` | Puerto SMTP. |
| `EMAIL_USE_TLS` | `True` | TLS para el correo. |
| `EMAIL_USE_SSL` | `False` | SSL para el correo. |
| `EMAIL_HOST_USER` | `correo@dominio.com` | Cuenta que envía los correos. |
| `EMAIL_HOST_PASSWORD` | contraseña de aplicación | Contraseña SMTP; nunca la contraseña normal del correo. |
| `DEFAULT_FROM_EMAIL` | `correo@dominio.com` | Remitente de los correos. |
| `CORREO_CONTACTO` | `contacto@kanview.com` | Correo visible en la interfaz. |
| `FACTURA_IVA` | `0` | Porcentaje de IVA de las facturas. |
| `EMPRESA_*` | datos del taller | Datos del emisor en la factura. |
| `TERMINOS_VERSION` | `1.0` | Versión vigente de los términos. |
| `BACKUP_DIR` | `backups` | Carpeta de copias de seguridad. |
| `BACKUP_RETENCION` | `10` | Cantidad de copias que se conservan. |
| `MAX_VIDEO_BYTES` | `26214400` | Tamaño máximo por video (25 MB). |
| `MAX_BYTES_MULTIMEDIA` | `62914560` | Tamaño máximo total por pedido (60 MB). |
| `PASSWORD_RESET_TIMEOUT` | `86400` | Vigencia del enlace de recuperación en segundos. |

### Correo en desarrollo

Si no tienes SMTP configurado, puedes imprimir los correos en la terminal:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Así podrás probar recuperación de contraseña, facturas y notificaciones sin
enviar correos reales.

### Variables de seguridad para producción

Cuando publiques el sistema con HTTPS, agrega o ajusta:

```env
DEBUG=False
ALLOWED_HOSTS=kanview.tudominio.com
CSRF_TRUSTED_ORIGINS=https://kanview.tudominio.com
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSP_REPORT_ONLY=False
```

No subas el archivo `.env` al repositorio: contiene credenciales y debe quedar
fuera de Git.

## 5. Preparar la base de datos

Aplica las migraciones:

```bash
python manage.py migrate
```

El proyecto usará `db.sqlite3` en la raíz. Para una instalación nueva, este
comando crea las tablas y los roles iniciales.

Crea el primer usuario administrador:

```bash
python manage.py createsuperuser
```

El superusuario puede entrar al panel de Django en `/admin/` y también usar la
interfaz de Kanview.

## 6. Levantar el servidor

```bash
python manage.py runserver
```

Abre en el navegador:

```text
http://127.0.0.1:8000/
```

El servidor de desarrollo usa Daphne/ASGI, por lo que también atiende los
WebSockets de la mensajería.

Para acceder desde otro equipo de la red local:

```bash
python manage.py runserver 0.0.0.0:8000
```

En ese caso agrega la IP o el nombre del equipo a `ALLOWED_HOSTS`:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
```

Detén el servidor con `Ctrl+C`.

## 7. Primeros pasos después de entrar

1. Inicia sesión con el superusuario.
2. Acepta los términos y condiciones si el sistema los solicita.
3. Entra a **Usuarios** y crea clientes y trabajadores.
4. Desde la ficha de cada persona, crea su cuenta de acceso y asigna su rol.
5. Crea los productos y su stock desde **Productos**.
6. Revisa el catálogo y crea un pedido de prueba.
7. Configura el correo SMTP si vas a enviar facturas o notificaciones reales.

## 8. Verificación y pruebas

Comprobar la configuración:

```bash
python manage.py check
```

Ejecutar la suite de pruebas:

```bash
python manage.py test kanview
```

La suite actual contiene **189 tests**.

Comprobar que no faltan migraciones:

```bash
python manage.py makemigrations --check --dry-run
```

## 9. Comandos útiles

```bash
# Activar el entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Crear administrador
python manage.py createsuperuser

# Levantar el servidor
python manage.py runserver

# Verificar configuración
python manage.py check

# Ejecutar pruebas
python manage.py test kanview

# Ver migraciones pendientes
python manage.py makemigrations --check --dry-run
```

## 10. Solución de problemas

### `ModuleNotFoundError: No module named 'django'`

El entorno virtual no está activo o no se instalaron las dependencias:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `no such table`

Faltan las migraciones:

```bash
python manage.py migrate
```

### `DisallowedHost`

Agrega el dominio o la IP a `ALLOWED_HOSTS` en `.env` y reinicia el servidor.

### Error CSRF al usar un dominio o HTTPS

Agrega el origen completo a `CSRF_TRUSTED_ORIGINS`:

```env
CSRF_TRUSTED_ORIGINS=https://kanview.tudominio.com
```

### Los correos no llegan

Revisa `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` y
`EMAIL_HOST_PASSWORD`. Para desarrollo, usa el backend de consola. En Gmail
debes usar una contraseña de aplicación, no la contraseña normal de la cuenta.

### WebSocket desconectado

En desarrollo usa `python manage.py runserver`, que arranca Daphne. Para
producción con varios procesos necesitas configurar `channels_redis` y un
servidor Redis compartido.

### Error 429

El sistema aplicó rate limit por demasiadas solicitudes. Espera el tiempo de la
ventana correspondiente antes de volver a intentar.

### No se pueden crear copias de seguridad

El sistema usa respaldos SQLite y solo Administración puede gestionarlos.
Verifica que `BACKUP_DIR` exista o que el proceso tenga permisos para crearlo.

## 11. Notas para producción

- Usa `DEBUG=False`.
- Define una `SECRET_KEY` única y privada.
- Configura `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y HTTPS.
- Activa cookies seguras, redirección SSL y HSTS.
- Configura un SMTP real.
- Mantén `db.sqlite3`, `media/` y `backups/` en almacenamiento persistente.
- Para varias instancias, usa Redis para Channels y para el cache del rate limit.
- Sirve archivos estáticos y de medios con un proxy web; las evidencias deben
  seguir pasando por las rutas protegidas de Kanview.
- Ejecuta `python manage.py test kanview` antes de desplegar.

```env
SECRET_KEY=una-clave-secreta-larga-y-única
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

Para generar una `SECRET_KEY` segura:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Variables principales

| Variable | Ejemplo | Uso |
|---|---|---|
| `SECRET_KEY` | cadena larga y aleatoria | Firma de sesiones, tokens y enlaces. Obligatoria en producción. |
| `DEBUG` | `True` en desarrollo | Activa el modo de depuración. En producción debe ser `False`. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Dominios o IPs desde los que se accede al sistema. |
| `EMAIL_HOST` | `smtp.gmail.com` | Servidor SMTP. |
| `EMAIL_PORT` | `587` | Puerto SMTP. |
| `EMAIL_USE_TLS` | `True` | TLS para el correo. |
| `EMAIL_USE_SSL` | `False` | SSL para el correo. |
| `EMAIL_HOST_USER` | `correo@dominio.com` | Cuenta que envía los correos. |
| `EMAIL_HOST_PASSWORD` | contraseña de aplicación | Contraseña SMTP; nunca la contraseña normal del correo. |
| `DEFAULT_FROM_EMAIL` | `correo@dominio.com` | Remitente de los correos. |
| `CORREO_CONTACTO` | `contacto@kanview.com` | Correo visible en la interfaz. |
| `FACTURA_IVA` | `0` | Porcentaje de IVA de las facturas. |
| `EMPRESA_*` | datos del taller | Datos del emisor en la factura. |
| `TERMINOS_VERSION` | `1.0` | Versión vigente de los términos. |
| `BACKUP_DIR` | `backups` | Carpeta de copias de seguridad. |
| `BACKUP_RETENCION` | `10` | Cantidad de copias que se conservan. |
| `MAX_VIDEO_BYTES` | `26214400` | Tamaño máximo por video (25 MB). |
| `MAX_BYTES_MULTIMEDIA` | `62914560` | Tamaño máximo total por pedido (60 MB). |
| `PASSWORD_RESET_TIMEOUT` | `86400` | Vigencia del enlace de recuperación en segundos. |

### Correo en desarrollo

Si no tienes SMTP configurado, puedes imprimir los correos en la terminal:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Así podrás probar recuperación de contraseña, facturas y notificaciones sin
enviar correos reales.

### Variables de seguridad para producción

Cuando publiques el sistema con HTTPS, agrega o ajusta:

```env
DEBUG=False
ALLOWED_HOSTS=kanview.tudominio.com
CSRF_TRUSTED_ORIGINS=https://kanview.tudominio.com
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSP_REPORT_ONLY=False
```

No subas el archivo `.env` al repositorio: contiene credenciales y debe quedar
fuera de Git.

## 5. Preparar la base de datos

Aplica las migraciones:

```bash
python manage.py migrate
```

El proyecto usará `db.sqlite3` en la raíz. Para una instalación nueva, este
comando crea las tablas y los roles iniciales.

Crea el primer usuario administrador:

```bash
python manage.py createsuperuser
```

El superusuario puede entrar al panel de Django en `/admin/` y también usar la
interfaz de Kanview.

## 6. Levantar el servidor

```bash
python manage.py runserver
```

Abre en el navegador:

```text
http://127.0.0.1:8000/
```

El servidor de desarrollo usa Daphne/ASGI, por lo que también atiende los
WebSockets de la mensajería.

Para acceder desde otro equipo de la red local:

```bash
python manage.py runserver 0.0.0.0:8000
```

En ese caso agrega la IP o el nombre del equipo a `ALLOWED_HOSTS`:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
```

Detén el servidor con `Ctrl+C`.

## 7. Primeros pasos después de entrar

1. Inicia sesión con el superusuario.
2. Acepta los términos y condiciones si el sistema los solicita.
3. Entra a **Usuarios** y crea clientes y trabajadores.
4. Desde la ficha de cada persona, crea su cuenta de acceso y asigna su rol.
5. Crea los productos y su stock desde **Productos**.
6. Revisa el catálogo y crea un pedido de prueba.
7. Configura el correo SMTP si vas a enviar facturas o notificaciones reales.

## 8. Verificación y pruebas

Comprobar la configuración:

```bash
python manage.py check
```

Ejecutar la suite de pruebas:

```bash
python manage.py test kanview
```

La suite actual contiene **189 tests**.

Comprobar que no faltan migraciones:

```bash
python manage.py makemigrations --check --dry-run
```

## 9. Comandos útiles

```bash
# Activar el entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Crear administrador
python manage.py createsuperuser

# Levantar el servidor
python manage.py runserver

# Verificar configuración
python manage.py check

# Ejecutar pruebas
python manage.py test kanview

# Ver migraciones pendientes
python manage.py makemigrations --check --dry-run
```

## 10. Solución de problemas

### `ModuleNotFoundError: No module named 'django'`

El entorno virtual no está activo o no se instalaron las dependencias:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### `no such table`

Faltan las migraciones:

```bash
python manage.py migrate
```

### `DisallowedHost`

Agrega el dominio o la IP a `ALLOWED_HOSTS` en `.env` y reinicia el servidor.

### Error CSRF al usar un dominio o HTTPS

Agrega el origen completo a `CSRF_TRUSTED_ORIGINS`:

```env
CSRF_TRUSTED_ORIGINS=https://kanview.tudominio.com
```

### Los correos no llegan

Revisa `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` y
`EMAIL_HOST_PASSWORD`. Para desarrollo, usa el backend de consola. En Gmail
debes usar una contraseña de aplicación, no la contraseña normal de la cuenta.

### WebSocket desconectado

En desarrollo usa `python manage.py runserver`, que arranca Daphne. Para
producción con varios procesos necesitas configurar `channels_redis` y un
servidor Redis compartido.

### Error 429

El sistema aplicó rate limit por demasiadas solicitudes. Espera el tiempo de la
ventana correspondiente antes de volver a intentar.

### No se pueden crear copias de seguridad

El sistema usa respaldos SQLite y solo Administración puede gestionarlos.
Verifica que `BACKUP_DIR` exista o que el proceso tenga permisos para crearlo.

## 11. Notas para producción

- Usa `DEBUG=False`.
- Define una `SECRET_KEY` única y privada.
- Configura `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y HTTPS.
- Activa cookies seguras, redirección SSL y HSTS.
- Configura un SMTP real.
- Mantén `db.sqlite3`, `media/` y `backups/` en almacenamiento persistente.
- Para varias instancias, usa Redis para Channels y para el cache del rate limit.
- Sirve archivos estáticos y de medios con un proxy web; las evidencias deben
  seguir pasando por las rutas protegidas de Kanview.
- Ejecuta `python manage.py test kanview` antes de desplegar.

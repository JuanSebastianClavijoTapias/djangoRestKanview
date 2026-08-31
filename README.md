# Kanview

Sistema de gestión para Cuir Tapicería (taller de tapicería en cuero): backend Django REST Framework más un conjunto de páginas de interfaz (Django templates) generadas a partir del diseño en Stitch.

## Requisitos

- Python 3.10 o superior
- pip

## Instalación

```bash
git clone <url-del-repo>
cd dragonfish

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Variables de entorno

Copia el archivo de ejemplo y ajusta los valores si es necesario:

```bash
cp .env.example .env
```

| Variable       | Descripción                                   | Default (`.env.example`)   |
|----------------|------------------------------------------------|-----------------------------|
| `SECRET_KEY`   | Clave secreta de Django                         | `change-me-generate-a-new-one` |
| `DEBUG`        | Modo debug                                      | `True`                      |
| `ALLOWED_HOSTS`| Hosts permitidos, separados por coma            | `localhost,127.0.0.1`       |

Para producción, genera una `SECRET_KEY` propia y pon `DEBUG=False`.

## Base de datos

El proyecto usa SQLite por defecto (no requiere instalar nada aparte). Aplica las migraciones:

```bash
python3 manage.py migrate
```

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

## Rutas

### API (Django REST Framework)

Todas bajo el prefijo `/api/`, con CRUD completo (`ModelViewSet`):

```
/api/clientes/
/api/empleados/
/api/administradores/
/api/analisis-financieros/
/api/productos/
/api/inventarios/
/api/catalogos/
/api/pedidos/
/api/tareas-pedido/
/api/actividades/
/api/historial/
/api/calendario/
```

### Interfaz (páginas)

```
/                  Tablero de pedidos (home)
/login/            Inicio de sesión
/pedidos/          Tablero de pedidos
/pedidos/<id>/     Detalle de pedido
/tareas/           Gestión de tareas
/calendario/       Calendario de producción
/inventario/       Inventario de materiales
/finanzas/         Análisis financiero
/auditoria/        Auditoría y control
/mensajeria/       Mensajería interna
/clientes/         Gestión de clientes
/empleados/         Gestión de empleados
/catalogo/         Catálogo de productos
/admin/            Panel de administración de Django
```

> Nota: estas páginas están construidas a partir del diseño exportado de Stitch. Por ahora muestran datos de ejemplo fijos en el HTML; todavía no están conectadas a los datos reales de la API (`/api/...`).

## Estructura del proyecto

```
config/     Configuración del proyecto Django (settings, urls raíz)
kanview/    App principal: modelos, serializers, views/urls de la API,
            y views/urls/templates de la interfaz
```

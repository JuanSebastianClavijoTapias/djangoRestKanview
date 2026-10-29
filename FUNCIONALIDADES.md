# Kanview · Funcionalidades del sistema

Kanview es un sistema de gestión para un taller de tapicería. Cubre la operación
del taller, el portal del cliente, la producción, la mensajería interna, la
facturación y la administración de usuarios y datos.

## Roles y alcance

| Rol | Puede hacer |
|---|---|
| **Administrador** | Todo: operación, usuarios, finanzas, auditoría, configuración, respaldos y mover tarjetas del tablero. |
| **Secretaría** | Operación, usuarios, finanzas, auditoría y configuración; no gestiona respaldos ni mueve tarjetas. |
| **Trabajador** | Pedidos, tareas, actividades, productos, catálogo, inventario, calendario y mensajería. Sin finanzas, auditoría, usuarios ni configuración. |
| **Cliente** | Catálogo, pedidos propios, solicitudes de cambio, evidencias propias, mensajería y perfil. No ve stock interno ni facturas. |

## 1. Acceso y seguridad

- Login con usuario, correo o documento de trabajador.
- Cuentas creadas únicamente por Administración o Secretaría; no hay registro público.
- Recuperación de contraseña por correo.
- Cambio de contraseña desde el perfil.
- Autenticación en dos pasos (2FA) con TOTP, código QR y códigos de respaldo.
- Aceptación obligatoria de términos y condiciones por versión.
- Perfil editable: nombre, correo, contraseña y seguridad.
- JWT para la API: access token, refresh, blacklist y OTP cuando la cuenta tiene 2FA.
- Sesiones web protegidas.
- Rate limit para login, recuperación, API y mensajería WebSocket.
- Protección CSRF, CSP, cookies `HttpOnly`/`SameSite`, HSTS configurable y cabeceras de seguridad.
- Evidencias protegidas por rol y propiedad, con enlaces públicos firmados y caducidad.
- Validación de archivos por tipo, contenido y tamaño.
- Auditoría de accesos y acciones relevantes.

## 2. Panel y navegación

- Panel con totales de clientes, trabajadores, productos y pedidos.
- Últimos pedidos registrados.
- Menú lateral filtrado según el rol.
- Buscador en el header de cada módulo.
- Vistas Kanban y lista.
- Modales de detalle.
- Interfaz responsive.
- El cliente entra directamente a sus procesos, sin panel interno.

## 3. Pedidos y producción

- CRUD de pedidos.
- Código automático `PED-0001`.
- Fecha y hora de creación automáticas.
- Fecha límite de entrega.
- Cliente, producto, cantidad, trabajador y descripción.
- Validación y descuento automático de stock.
- Devolución de stock al desactivar o eliminar un pedido.
- Ajuste de stock al editar cantidad o producto.
- Tablero Kanban: **Pendiente**, **En proceso** y **Completado**.
- Movimiento de tarjetas por drag & drop; solo el Administrador puede moverlas.
- Estado manual del tablero o estado calculado desde las actividades.
- Vista alternativa en tabla.
- Búsqueda por código, cliente, producto, trabajador o descripción.
- Detalle completo del pedido.
- Aprobación con asignación de trabajador.
- Rechazo con motivo.
- Notificaciones y correos al cliente.
- Galería de imágenes y videos.
- Carga de hasta 5 archivos: imágenes de 5 MB y videos de 25 MB.
- Edición y eliminación de evidencias.
- Envío de evidencias al cliente por correo con enlaces firmados.
- Solicitudes de modificación del cliente.
- El cliente puede crear, editar o eliminar solicitudes pendientes.
- Administración/Secretaría puede aceptar o rechazar solicitudes y responder.
- Historial cronológico del pedido.
- Factura PDF con numeración `FAC-0001`, subtotal, IVA configurable y total.
- Descarga y envío de factura por correo.
- Las facturas solo las consulta el personal, no el cliente.

## 4. Tareas y actividades

- CRUD de tareas y actividades.
- Tarea asociada a un pedido y a un responsable opcional.
- Actividad asociada a una tarea y a un trabajador obligatorio.
- Tablero Kanban de tareas: **Pendiente**, **En progreso** y **Completado**.
- Drag & drop de tareas y actividades.
- Filtro de tareas por trabajador.
- Progreso de cada tarea según actividades completadas.
- Detalle de tarea con todas sus actividades.
- Confirmación de tarea solo cuando todas sus actividades están completadas.
- Puede confirmar el responsable, un trabajador del área o Administración.
- Incremento automático de tareas realizadas del trabajador.
- Tablero de actividades agrupado por estado.
- Filtros de actividades por área/cargo y trabajador.
- Cambio de estado con notificaciones al área, al staff y al cliente.
- Validación de fechas: las tareas y actividades deben quedar entre la fecha de
  registro y la fecha límite del pedido.
- El formulario permite seleccionar primero el pedido o la tarea.
- Los calendarios deshabilitan los días fuera de la ventana del pedido.
- La misma validación se aplica en la API.
- Eliminación lógica con reactivación.

## 5. Productos, catálogo e inventario

- CRUD de productos.
- Categorías: tela, espuma, madera, herraje, hilo y otros.
- Código, nombre, descripción, precio y cantidad en stock.
- `Producto.cantidad` es la única fuente de verdad del inventario.
- Catálogo de solo lectura con búsqueda y filtro por categoría.
- Tarjeta destacada y tarjetas secundarias.
- Ficha de producto con descripción, categoría, precio y disponibilidad.
- Historial gráfico de pedidos de los últimos 6 meses.
- El cliente ve “Disponible” o “Agotado”, sin cifras internas de stock.
- Botón para que el cliente cree un pedido desde el catálogo.
- Vista de inventario/existencias con stock total, agotados y stock bajo.
- Alertas de stock bajo o agotado.
- Desactivación y reactivación de productos.

## 6. Clientes, trabajadores y usuarios

- Módulo Usuarios con clientes y trabajadores.
- Ficha de cada cliente o trabajador.
- Creación de cuenta de acceso vinculada explícitamente a la persona.
- Asignación de rol.
- Contraseña temporal para cuentas nuevas.
- Activación y desactivación de cuentas.
- Protección contra reutilización o apropiación de correos y cuentas ajenas.
- CRUD de clientes.
- CRUD de trabajadores con cargo, salario, fecha de nacimiento, edad calculada y tareas realizadas.
- CRUD de administradores.
- Portal del cliente con sus propios pedidos, evidencias y solicitudes.
- El cliente no puede acceder a pedidos, evidencias ni datos de otros clientes.

## 7. Calendario

- Calendario mensual de producción.
- Navegación entre meses.
- Búsqueda por pedido, cliente, producto o descripción.
- Eventos de pedidos con fecha límite de entrega.
- Asignación de un pedido a una fecha del calendario.
- Eventos personales sin pedido asociado.
- Título, descripción, hora de inicio y hora límite.
- Recordatorios configurables por minutos antes.
- Prohibición de crear eventos en fechas pasadas.
- Validación de horarios.
- Recordatorios vencidos convertidos en notificaciones.
- CRUD y reactivación de registros del calendario.

## 8. Mensajería

- Chat interno directo entre usuarios.
- Contactos filtrados según el rol:
  - Administración/Secretaría pueden hablar con clientes y trabajadores.
  - Clientes ven trabajadores asignados y conversaciones ya iniciadas.
  - Trabajadores ven sus clientes y conversaciones iniciadas por Administración.
- Mensajería en tiempo real con WebSocket.
- Envío alternativo por HTTP.
- Contador de mensajes no leídos.
- Marcación automática de mensajes como leídos.
- Rate limit de mensajes por conexión WebSocket.
- Escape de HTML en mensajes para prevenir XSS.

## 9. Notificaciones

- Campana con avisos calculados:
  - Tareas vencidas.
  - Pedidos vencidos o próximos a vencer.
  - Pedidos sin evidencias cargadas.
  - Productos agotados o con stock bajo.
- Notificaciones persistentes para pedidos, tareas, actividades, facturas,
  seguridad y calendario.
- Marcación de notificaciones como leídas.
- El cliente solo recibe avisos de sus propios pedidos.
- Notificaciones por correo para eventos importantes.
- Recordatorios de calendario.

## 10. Finanzas y facturación

- Dashboard financiero con ingresos, gastos, balance, margen y productos vendidos.
- Flujo de caja de 3, 6 o 12 meses.
- Distribución de ingresos por fuente.
- Fuentes: venta directa, mayorista, proyecto personalizado y otros.
- Búsqueda por administrador o fuente.
- CRUD de análisis financieros.
- Acceso limitado a Administración y Secretaría.
- Facturas PDF con datos del pedido, cliente, producto, subtotal, IVA y total.
- Envío de factura por correo.

## 11. Auditoría, respaldos y configuración

- Historial operativo por pedido.
- Log general de auditoría con filtros por acción, texto, usuario y fecha.
- Paginación del log.
- Registro de login, 2FA, cambios de contraseña, CRUD, aprobaciones, facturas y respaldos.
- Copias de seguridad de SQLite.
- Listado, creación y restauración de respaldos.
- Verificación de integridad antes de restaurar.
- Copia de seguridad previa automática antes de una restauración.
- Retención configurable de respaldos.
- Solo Administración puede crear o restaurar respaldos.
- Pantalla de configuración con roles, permisos y contacto.
- Configuración por variables de entorno para empresa, IVA, SMTP, términos,
  backups y límites de archivos.

## 12. API REST

- API con Django REST Framework.
- Recursos con listar, crear, consultar, actualizar y desactivar:
  - Clientes.
  - Empleados.
  - Administradores.
  - Análisis financieros.
  - Productos.
  - Pedidos.
  - Tareas de pedido.
  - Actividades.
  - Historial.
  - Calendario.
- Autenticación por sesión o JWT.
- Tokens de acceso, refresh y blacklist.
- Permisos por rol en cada recurso.
- El cliente solo puede consultar sus propios pedidos.
- Eliminación lógica: desactiva en lugar de borrar.
- Validación de fechas de tareas y actividades también en la API.

## 13. Calidad técnica

- Django 6.1.
- Django REST Framework.
- Channels/Daphne para WebSockets.
- SQLite como base de datos por defecto.
- ReportLab para generación de PDF.
- SimpleJWT para autenticación.
- **189 tests automatizados pasando.**
- `manage.py check` limpio.
- `makemigrations --check` sin cambios pendientes.

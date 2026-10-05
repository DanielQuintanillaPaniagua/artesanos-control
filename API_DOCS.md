# API REST — Artesanos Control

Documentación completa de la API REST de Artesanos Control.

**Base URL:** `https://artesanos-control.duckdns.org/api`

**Autenticación:** Todas las rutas requieren sesión activa (cookie de Flask-Login).

---

## Índice

- [Autenticación](#autenticación)
- [Dashboard](#dashboard)
- [Usuarios](#usuarios)
- [Sucursales](#sucursales)
- [Proveedores](#proveedores)
- [Categorías](#categorías)
- [Reportes](#reportes)
- [IA](#ia)

---

## Convenciones

### Formato de respuesta exitosa

```json
{
    "success": true,
    "data": { ... },
    "message": "Operación exitosa"
}
Formato de error
{
    "success": false,
    "error": "Descripción del error"
}
Códigos HTTP
Código    Significado
200    OK
201    Creado
400    Error de validación
401    No autenticado
403    Sin permisos
404    No encontrado
500    Error del servidor
Permisos
Owner: acceso total

Empleado: solo lectura de su sucursal

Autenticación
Login
POST /auth/login
Parámetro    Tipo    Descripción
usuario    string    Nombre de usuario
password    string    Contraseña
Respuesta: redirección a /dashboard o error.

Logout
GET /auth/logout
Dashboard
GET /api/dashboard/stats
Métricas generales del periodo.

Query params:

desde (date, opcional) — ej: 2026-09-01

hasta (date, opcional) — ej: 2026-09-30

sucursal (int, opcional) — ID de sucursal

Respuesta:
{
    "success": true,
    "periodo": {"desde": "2026-09-01", "hasta": "2026-09-30"},
    "stats": {
        "total_facturas": 48,
        "total_monto": 6240.50,
        "validadas": 46,
        "observadas": 2,
        "porcentaje_validacion": 95.8
    }
}
GET /api/dashboard/facturas-por-sucursal
Desglose por sucursal.

GET /api/dashboard/facturas-por-categoria
Top categorías por monto.

Query params:

limite (int, default 10)

GET /api/dashboard/facturas-por-dia
Serie temporal de los últimos N días.

Query params:

dias (int, default 7, max 90)

GET /api/dashboard/top-proveedores
Top proveedores por monto.

Query params:

limite (int, default 5)

GET /api/dashboard/alerts
Facturas observadas del periodo.

GET /api/dashboard/resumen
Todo en uno (stats + sucursales + categorías).

Usuarios
GET /api/usuarios/
Listar usuarios.

Query params:

rol (string) — owner / empleado

estado (string) — Activo / Inactivo

sucursal (int)

Permiso: owner

GET /api/usuarios/<id>
Ver un usuario.

POST /api/usuarios/
Crear usuario.

Body:
{
    "nombre": "Juan Perez",
    "usuario": "jperez",
    "email": "jperez@artesanos.com",
    "rol": "empleado",
    "sucursal_id": 1,
    "password": "secreto123"
}
PUT /api/usuarios/<id>
Actualizar usuario. Mismo body que POST (password opcional).

DELETE /api/usuarios/<id>
Desactivar usuario (soft delete).

POST /api/usuarios/<id>/toggle-estado
Alternar activo/inactivo.

Sucursales
GET /api/sucursales/
Listar sucursales.

Query params:

estado (string) — Activa / Inactiva

stats (bool) — incluir conteos

GET /api/sucursales/<id>
Ver sucursal con estadísticas.

POST /api/sucursales/
Crear sucursal (solo owner).

Body:
{
    "nombre": "Usulutan",
    "direccion": "Calle Principal #123",
    "telefono": "+503 2600 1111",
    "estado": "Activa"
}
PUT /api/sucursales/<id>
Actualizar sucursal.

DELETE /api/sucursales/<id>
Desactivar sucursal. Falla si tiene facturas asociadas.

POST /api/sucursales/<id>/toggle-estado
Alternar activa/inactiva.

Proveedores
GET /api/proveedores/
Listar proveedores.

Query params:

estado (string)

buscar (string)

stats (bool)

GET /api/proveedores/<id>
Ver proveedor con estadísticas.

POST /api/proveedores/
Crear proveedor.

Body:
{
    "nombre": "Distribuidora La Central",
    "telefono": "+503 2222 4444",
    "email": "ventas@lacentral.com"
}
PUT /api/proveedores/<id>
Actualizar proveedor.

DELETE /api/proveedores/<id>
Desactivar proveedor.

POST /api/proveedores/<id>/toggle-estado
Alternar activo/inactivo.

Categorías
GET /api/categorias/
Listar categorías (21 en total).

Query params:

estado (string)

grupo (string)

stats (bool)

La respuesta incluye un campo por_grupo con las categorías agrupadas.

GET /api/categorias/grupos
Listar grupos únicos.

GET /api/categorias/<id>
Ver categoría.

POST /api/categorias/
Crear categoría (solo owner).

PUT /api/categorias/<id>
Actualizar categoría (solo owner).

DELETE /api/categorias/<id>
Desactivar categoría (solo owner).

POST /api/categorias/<id>/toggle-estado
Alternar activa/inactiva.

Reportes
GET /api/reportes/facturas
Facturas en JSON con filtros.

Query params:

desde (date)

hasta (date)

sucursal (int)

estado (string)

GET /api/reportes/usuarios
Usuarios en JSON.

GET /api/reportes/sucursales
Sucursales con estadísticas del mes.

GET /api/reportes/resumen
Resumen general de todos los recursos.

GET /api/reportes/facturas.xlsx
Descarga el Excel de facturas.

GET /api/reportes/usuarios.xlsx
Descarga el Excel de usuarios.

GET /api/reportes/sucursales.xlsx
Descarga el Excel de sucursales.

IA
POST /api/ai/chat
Chat con Artesanos AI (Google Gemini).

Body:
{
    "mensaje": "Cuanto se gasto este mes?",
    "historial": []
}
Respuesta:

json
{
    "ok": true,
    "respuesta": "En el mes actual, el gasto total fue de $6,240.50..."
}
Permiso: owner

Ejemplos con cURL
Obtener stats del dashboard
curl -X GET "http://localhost:5000/api/dashboard/stats" \
     -b cookies.txt
Crear un usuario
curl -X POST "http://localhost:5000/api/usuarios/" \
     -H "Content-Type: application/json" \
     -b cookies.txt \
     -d '{
         "nombre": "Test User",
         "usuario": "test",
         "password": "test123",
         "rol": "empleado",
         "sucursal_id": 1
     }'
Descargar Excel de facturas
curl -X GET "http://localhost:5000/api/reportes/facturas.xlsx?desde=2026-09-01" \
     -b cookies.txt \
     -o facturas.xlsx
Probar con Postman
Importar la colección: artesanos-control.postman_collection.json

Configurar variable base_url = http://localhost:5000

Hacer login primero (guardar cookies automáticamente)

Probar los endpoints

Última actualización: Octubre 2026

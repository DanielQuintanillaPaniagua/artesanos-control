<div align="center">

# 🍕 ARTESANOS CONTROL

**Sistema web de control y validación de facturas para ARTESANOS PIZZERÍA**

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)
![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-4285F4?logo=googlegemini&logoColor=white)
![AWS](https://img.shields.io/badge/Deploy-AWS%20Lightsail-FF9900?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/Licencia-Privada-red)

</div>

---

## 📖 Descripción

**ARTESANOS CONTROL** es una aplicación Flask hecha para una empresa salvadoreña real, con distintas sucursales. Reemplaza el control de compras en Excel por un sistema centralizado.

Cada empleado registra las facturas de compra de su sucursal con un **desglose obligatorio por categorías** (Comida, Bebida, Limpieza, etc.). Antes de guardar, el sistema valida que **la suma de las categorías sea exactamente igual al total de la factura**; si no cuadra, bloquea el guardado.

El **owner** puede registrar facturas en cualquier sucursal, revisarlas, corregirlas cuando hay errores (con historial de cambios) y consultar todo desde un panel global, incluyendo un asistente de IA basado en Google Gemini.

> 💡 La validación la hace el backend en Python. La IA solo consulta y resume datos ya validados; **nunca participa en la validación**.

---

## ✨ Características

### 🔐 Autenticación y seguridad

- Login con **3 roles**: **Owner**, **Supervisor** y **Empleado**
- Contraseñas hasheadas con **scrypt** (Werkzeug)
- Recuperación de contraseña por email con token temporal
- Protección **CSRF** en formularios y endpoints AJAX
- Bloqueo de acceso a sucursales inactivas (capa 8 en 8 niveles)
- Permisos granulares por rol y sucursal

### 🧾 Gestión de facturas

- Registro con validación automática de cuadre
- **21 categorías de gasto iniciales** basadas en el Excel real de la empresa; el owner puede crear más desde el mismo formulario
- **Tipos de documento configurables** (FCC, FC, Nota de envío, Crédito fiscal, etc.), administrados por el owner
- **Selector de proveedor con buscador** y alta rápida de proveedores desde el formulario
- El owner puede registrar facturas eligiendo la sucursal
- Edición por el owner y el supervisor con **historial de correcciones**
- Filtros por sucursal, rango de fechas y estado
- Bloqueo si el desglose supera el total (los empleados no pueden guardar descuadres)
- Modo offline con sincronización automática

### 💬 Chat entre sucursales

- **Chat General** para coordinación entre todas las sucursales
- **Chat directo 1 a 1** entre supervisores y con el owner
- Actualización automática cada 10 segundos (polling)
- Contador de mensajes no leídos
- Modal para iniciar chats directos

### 🛠️ Panel de administración

- CRUD de usuarios y sucursales (crear, editar, activar/desactivar)
- **Catálogo**: activar/desactivar categorías, proveedores y tipos de documento (no se borran, para conservar el historial)
- Reseteo de contraseña de cualquier usuario
- Dashboard con métricas por sucursal y gráficas por período (hoy, ayer, últimos 7 días, mes) con vista en porcentaje o monto
- Reportes exportables en **CSV y Excel**
- Importación de facturas desde Excel por sucursal (asigna solo proveedores ya existentes; no crea proveedores nuevos)
- Configuración del sistema: backups, monitoreo y logs
- Backup manual de la base de datos con rotación

### 🤖 Artesanos AI

- Chat en lenguaje natural con **Google Gemini**
- Contexto real de facturas, proveedores y sucursales (filtrado por sucursal)
- Preguntas sugeridas para consultas rápidas
- Acceso exclusivo para administradores y supervisores

---

## 🧰 Tecnologías

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.9+ · Flask 3.1 |
| ORM | SQLAlchemy · Flask-SQLAlchemy |
| Base de datos | MySQL 8 (producción) · MariaDB vía XAMPP (local) |
| Autenticación | Flask-Login · Werkzeug Security (scrypt) |
| Seguridad | Flask-WTF (CSRF) · Flask-Limiter |
| Frontend | HTML5 · CSS3 · JavaScript · Bootstrap 5.3 |
| IA | Google Gemini API (`google-genai`) |
| Emails | SMTP vía Gmail |
| Excel | openpyxl |
| Monitoreo | psutil |
| Deploy | AWS Lightsail · Nginx · Gunicorn · systemd |
| HTTPS | Let's Encrypt · Certbot |
| Dominio | DuckDNS |

---

## 🚀 Instalación

> 📘 **Guía completa paso a paso: [INSTALACION.md](INSTALACION.md)** (instalación local y en servidor Ubuntu con Nginx, Gunicorn y HTTPS).

### Resumen rápido (local)

**Requisitos:** Python 3.9+, MySQL/MariaDB (XAMPP en Windows) y Git.

```bash
git clone https://github.com/DanielQuintanillaPaniagua/artesanos-control.git
cd artesanos-control

python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell   (Linux/macOS: source venv/bin/activate)

pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env   -> editar valores
```

Crea la base de datos vacía (en MySQL/XAMPP):

```sql
CREATE DATABASE artesanos_control CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

Crea las tablas y los datos iniciales, y arranca:

```bash
python crear_admin.py
python run.py
```

Abre <http://127.0.0.1:5000>.

> En local usa `FLASK_ENV=development` en el `.env`. En producción se exige HTTPS y definir `SERVER_NAME` (ver [INSTALACION.md](INSTALACION.md)).

### 🔑 Credenciales iniciales

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Owner | `owner` | `artesanos2026` |

> ⚠️ **IMPORTANTE:** cambia la contraseña después del primer inicio de sesión.

---

## 🗂️ Estructura del proyecto

```text
artesanos-control/
├── app/
│   ├── __init__.py              # Application Factory
│   ├── models/                  # Modelos SQLAlchemy
│   │   ├── user.py              # User + PasswordResetToken
│   │   ├── sucursal.py
│   │   ├── proveedor.py
│   │   ├── categoria.py
│   │   ├── factura.py
│   │   ├── detalle_factura.py
│   │   ├── historial_correccion.py
│   │   ├── tipo_documento.py
│   │   └── chat.py              # Conversacion + Mensaje + ConversacionMiembro
│   ├── routes/                  # Blueprints
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── facturas.py
│   │   ├── facturas_ui.py
│   │   ├── editar_factura.py
│   │   ├── admin.py
│   │   ├── perfil.py
│   │   ├── recuperar.py
│   │   ├── artesanos_ai.py
│   │   ├── ai_api.py
│   │   ├── chat_api.py
│   │   ├── chat_ui.py
│   │   ├── dashboard_api.py
│   │   ├── usuarios_api.py
│   │   ├── sucursales_api.py
│   │   ├── proveedores_api.py
│   │   ├── categorias_api.py
│   │   └── reportes_api.py
│   ├── services/                # Lógica de negocio
│   │   ├── validacion.py
│   │   ├── email_service.py
│   │   ├── system_service.py
│   │   ├── excel_service.py
│   │   └── artesanos_ai.py
│   ├── utils/
│   │   └── permisos.py          # Decoradores de permisos
│   ├── templates/               # Templates Jinja2
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── perfil.html
│   │   ├── api_docs.html
│   │   ├── admin/               # catalogo, usuarios, sucursales, importar, configuracion
│   │   ├── facturas/
│   │   ├── artesanos-ai/
│   │   ├── recuperar/
│   │   └── chat/
│   ├── static/                  # CSS, JS, imágenes
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   └── instance/                # SQLite (solo desarrollo)
├── backups/                     # Backups de BD (gitignored)
├── .env                         # Variables de entorno (NO va en git)
├── .env.example                 # Plantilla de variables
├── .gitignore
├── requirements.txt
├── crear_admin.py               # Crea tablas + datos iniciales (se puede repetir)
├── run.py                       # Arranque del servidor
├── INSTALACION.md               # Guia de instalacion
├── API_DOCS.md                  # Documentacion de la API
└── fix_errores.py               # Script de un solo uso (mantenimiento)
```

---

## ☁️ Deploy a producción

### Arquitectura

```mermaid
flowchart LR
    A[Cliente] -->|HTTPS 443| B[Nginx]
    B -->|socket| C[Gunicorn]
    C --> D[Flask]
    D --> E[(MySQL)]
```

### Servidor

| Componente | Detalle |
|------------|---------|
| Proveedor | AWS Lightsail (1 GB RAM, 2 vCPU) |
| Sistema operativo | Ubuntu 24.04 LTS |
| Región | US East (Ohio) |
| Gunicorn | `/etc/systemd/system/artesanos.service` (1 worker + 4 threads) |
| Nginx | `/etc/nginx/sites-available/artesanos` (proxy inverso) |
| SSL | Let's Encrypt con renovación automática vía Certbot |

### Actualizar producción

```bash
ssh -i /ruta/a/tu/llave.pem ubuntu@IP_DEL_SERVIDOR
cd /home/ubuntu/artesanos-control
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python crear_admin.py          # crea tablas nuevas si la version las trae (no borra datos)
sudo systemctl restart artesanos.service
```

> Instalar un servidor nuevo desde cero: ver [INSTALACION.md](INSTALACION.md#3-parte-b-instalación-en-servidor-ubuntu).

### Backup de la base de datos

**Opción 1: desde el panel.** Ve a `/admin/configuracion` y pulsa **"Crear backup ahora"**.

**Opción 2: desde la terminal.** MySQL te pedirá la contraseña de forma interactiva, así no queda guardada en el historial del shell ni en el repo:

```bash
mysqldump -u artesanos -p --no-tablespaces artesanos_control > backup_$(date +%Y%m%d).sql
```

---

## ⚙️ Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Clave secreta de Flask | Generar con `secrets` |
| `SQLALCHEMY_DATABASE_URI` | URI de conexión a MySQL | `mysql+pymysql://user:pass@host/db` |
| `FLASK_ENV` | Entorno de Flask | `development` / `production` |
| `FLASK_DEBUG` | Modo debug (`False` por defecto) | `True` / `False` |
| `SERVER_NAME` | **Obligatoria en producción**: dominio del sitio (sin `https://`) | `tu-dominio.com` |
| `PREFERRED_URL_SCHEME` | Esquema de las URLs generadas | `https` |
| `PORT` | Puerto en local (por defecto 5000) | `5000` |
| `RATELIMIT_STORAGE_URI` | Almacén del límite de intentos (opcional; con varios workers usar Redis) | `redis://localhost:6379/0` |
| `SMTP_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | `correo@gmail.com` |
| `SMTP_PASSWORD` | Contraseña de aplicación de Gmail | 16 caracteres |
| `SMTP_FROM` | Remitente de los correos | `Artesanos Control <correo@gmail.com>` |
| `GEMINI_API_KEY` | API key de Google Gemini | `AIza...` |

> 🔒 Nunca subas `.env` al repositorio. En producción usa `FLASK_ENV=production`, `FLASK_DEBUG=False` y define `SERVER_NAME`; el sitio debe servirse por **HTTPS** o las sesiones no funcionarán.

---

## 🌿 Flujo de ramas

| Rama | Propósito |
|------|-----------|
| `main` | Rama estable (producción) |
| `daniel-pre-production` | Desarrollo y pruebas previas a producción |
| `feature/xxx` | Nuevas funcionalidades |

---

## 📌 Versiones

| Versión | Fecha | Cambios principales |
|---------|-------|---------------------|
| v1.0.0 | Octubre 2026 | Primera versión estable: 3 roles, chat interno, CSRF, API REST completa, IA con Gemini |
| v1.3.0 | Noviembre 2026 | Tipos de documento configurables, catálogo con activar/desactivar, gráficas por período, buscador de proveedores, el owner registra facturas, pie de página, corrección de fechas (UTC) y de proveedores duplicados |

---

## 👥 Equipo

| Integrante | Rol | GitHub |
|------------|-----|--------|
| **Daniel Quintanilla Paniagua** | Desarrollador principal | [@DanielQuintanillaPaniagua](https://github.com/DanielQuintanillaPaniagua) |
| David Roberto Sánchez Rodríguez | Colaborador | [@David2689](https://github.com/David2689) |
| David Alberto Beltrán Rivas | Colaborador | [@davidrivaszz](https://github.com/davidrivaszz) |
| Kevin Manrique Campos Granados | Colaborador | [@kevin67883](https://github.com/kevin67883) |
| José Luis Gracia Mejía | Colaborador | [@jgjose](https://github.com/jgjose) |

---

## 📄 Licencia

Proyecto privado de **ARTESANOS PIZZERÍA**. Todos los derechos reservados.

---

<div align="center">

Hecho con 🐍 por [Daniel Quintanilla](https://github.com/DanielQuintanillaPaniagua) · Usulután, El Salvador 🇸🇻

*Última actualización: noviembre de 2026*

</div>
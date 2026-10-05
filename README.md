<div align="center">

# 🍕 ARTESANOS CONTROL

**Sistema web de control y validación de facturas para ARTESANOS PIZZERÍA**

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap&logoColor=white)
![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-4285F4?logo=googlegemini&logoColor=white)
![AWS](https://img.shields.io/badge/Deploy-AWS%20Lightsail-FF9900?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/Licencia-Privada-red)

</div>

---

## 📖 Descripción

**ARTESANOS CONTROL** es una aplicación Flask hecha para una empresa salvadoreña real, con sucursales en **San Salvador, Usulután y San Miguel**. Reemplaza el control de compras en Excel por un sistema centralizado.

Cada empleado registra las facturas de compra de su sucursal con un **desglose obligatorio por categorías** (Comida, Bebida, Limpieza, etc.). Antes de guardar, el sistema valida que **la suma de las categorías sea exactamente igual al total de la factura**; si no cuadra, bloquea el guardado.

El **owner** no registra facturas: las revisa, las corrige cuando hay errores (con historial de cambios) y consulta todo desde un panel global, incluyendo un asistente de IA basado en Google Gemini.

> 💡 La validación la hace el backend en Python. La IA solo consulta y resume datos ya validados; **nunca participa en la validación**.

---

## ✨ Características

### 🔐 Autenticación y seguridad

- Login con roles: **Owner** y **Empleado** (sesión ligada a una sucursal)
- Contraseñas hasheadas con **scrypt** (Werkzeug)
- Recuperación de contraseña por email con token temporal
- Bloqueo de acceso a sucursales inactivas
- Permisos granulares por rol

### 🧾 Gestión de facturas

- Registro con validación automática de cuadre
- **21 categorías de gasto** basadas en el Excel real de la empresa
- Edición por el owner con **historial de correcciones**
- Filtros por sucursal, rango de fechas y estado
- Bloqueo si el desglose supera el total de la factura
- Modo offline con sincronización automática

### 🛠️ Panel de administración

- CRUD de usuarios y sucursales (crear, editar, activar/desactivar)
- Reseteo de contraseña de cualquier usuario
- Dashboard con métricas por sucursal
- Reportes exportables en **CSV y Excel**
- Importación de facturas desde Excel
- Configuración del sistema: backups, monitoreo y logs
- Backup manual de la base de datos con rotación

### 🤖 Artesanos AI

- Chat en lenguaje natural con **Google Gemini**
- Contexto real de facturas, proveedores y sucursales
- Preguntas sugeridas para consultas rápidas
- Acceso exclusivo para administradores

---

## 🧰 Tecnologías

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.9+ · Flask 3.0 |
| ORM | SQLAlchemy · Flask-SQLAlchemy |
| Base de datos | MySQL 8 (producción) · MariaDB vía XAMPP (local) |
| Autenticación | Flask-Login · Werkzeug Security (scrypt) |
| Migraciones | Flask-Migrate |
| Frontend | HTML5 · CSS3 · JavaScript · Bootstrap 5.3 |
| IA | Google Gemini API |
| Emails | SMTP vía Gmail |
| Excel | openpyxl |
| Monitoreo | psutil |
| Deploy | AWS Lightsail · Nginx · Gunicorn · systemd |
| HTTPS | Let's Encrypt · Certbot |
| Dominio | DuckDNS |

---

## 🚀 Instalación local

### Requisitos previos

- Python 3.9 o superior
- MySQL o MariaDB (XAMPP recomendado en Windows)
- Git

### Pasos

**1. Clonar el repositorio**

```bash
git clone https://github.com/DanielQuintanillaPaniagua/artesanos-control.git
cd artesanos-control
```

**2. Crear y activar el entorno virtual**

```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

**3. Instalar dependencias**

```bash
pip install -r requirements.txt
```

**4. Configurar variables de entorno**

Copia la plantilla y edítala con tus valores (ver la [tabla de variables](#-variables-de-entorno)):

```bash
cp .env.example .env
```

```env
FLASK_SECRET_KEY=tu_clave_secreta
SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:@127.0.0.1/artesanos_control
FLASK_ENV=development
FLASK_DEBUG=True
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=tu_app_password_de_gmail
SMTP_FROM=Artesanos Control <tu_correo@gmail.com>
GEMINI_API_KEY=tu_api_key_de_gemini
```

**5. Crear la base de datos** (en MySQL/XAMPP)

```sql
CREATE DATABASE artesanos_control CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

**6. Crear las tablas y los datos iniciales**

```bash
python crear_admin.py
```

**7. Arrancar el servidor**

```bash
python run.py
```

**8. Abrir en el navegador:** <http://127.0.0.1:5000>

### 🔑 Credenciales por defecto

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Admin | `admin` | Ver `crear_admin.py` |

> ⚠️ **IMPORTANTE:** cambia la contraseña del admin después del primer login.

---

## 🗂️ Estructura del proyecto

```
artesanos-control/
├── app/
│   ├── __init__.py              # Application Factory
│   ├── models/                  # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── sucursal.py
│   │   ├── proveedor.py
│   │   ├── categoria.py
│   │   ├── factura.py
│   │   ├── detalle_factura.py
│   │   └── historial_correccion.py
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
│   │   └── ai_api.py
│   ├── services/                # Lógica de negocio
│   │   ├── validacion.py
│   │   ├── email_service.py
│   │   ├── system_service.py
│   │   ├── excel_service.py
│   │   └── artesanos_ai.py
│   ├── templates/               # Templates Jinja2
│   ├── static/                  # CSS, JS, imágenes
│   └── instance/                # SQLite (solo desarrollo)
├── migrations/                  # Flask-Migrate
├── backups/                     # Backups de BD (gitignored)
├── .env                         # Variables de entorno (NO va en git)
├── .env.example                 # Plantilla de variables
├── .gitignore
├── requirements.txt
├── crear_admin.py
└── run.py
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
sudo systemctl restart artesanos.service
```

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
| `FLASK_DEBUG` | Modo debug | `True` / `False` |
| `SMTP_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | `correo@gmail.com` |
| `SMTP_PASSWORD` | Contraseña de aplicación de Gmail | 16 caracteres |
| `SMTP_FROM` | Remitente de los correos | `Artesanos Control <correo@gmail.com>` |
| `GEMINI_API_KEY` | API key de Google Gemini | `AIza...` |

> 🔒 Nunca subas `.env` al repositorio. En producción usa `FLASK_ENV=production` y `FLASK_DEBUG=False`.

---

## 🌿 Flujo de ramas

| Rama | Propósito |
|------|-----------|
| `main` | Rama estable (producción) |
| `daniel-pre-production` | Desarrollo y pruebas previas a producción |
| `feature/xxx` | Nuevas funcionalidades |

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

Hecho con 🐍 Usulután, El Salvador 🇸🇻

*Última actualización: octubre de 2026*

</div>

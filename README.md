# ARTESANOS CONTROL

Sistema web de control y validacion de facturas para **ARTESANOS PIZZERIA**, una empresa salvadorena con 3 sucursales (Usulutan, San Salvador, San Miguel).

## Descripcion

Aplicacion Flask que permite a los empleados de cada sucursal registrar facturas de compra, con un desglose obligatorio por categorias (Comida, Bebida, Limpieza, etc.). El sistema valida que la suma de categorias coincida con el total de la factura antes de guardarla, evitando errores de cuadre.

Incluye un panel de administracion completo para el owner, con gestion de usuarios, sucursales, reportes exportables y un asistente de IA basado en Google Gemini.

## Caracteristicas

### Autenticacion y seguridad
- Login con roles (Owner / Empleado)
- Hashing de contrasenas con scrypt (Werkzeug)
- Recuperacion de contrasena por email con token temporal
- Bloqueo de sucursales inactivas (capa 8 en 6 niveles)
- Permisos granulares por rol

### 
- Registro con validacion automatica de cuadre
- 21 categorias de gasto (segun Excel de la empresa)
- Edicion de facturas por el owner con historial de cambios
- Filtros por sucursal, rango de fechas y estado
- Bloqueo de superar el total de la factura (capa 8)
- Modo offline con sincronizacion automatica

### Panel de administracion
- CRUD de usuarios (crear, editar, activar/desactivar)
- CRUD de sucursales (crear, editar, activar/desactivar)
- Resetear contrasena de cualquier usuario
- Dashboard con metricas por sucursal
- Reportes exportables (CSV y Excel)
- Importacion de facturas desde Excel
- Configuracion del sistema (backup, monitoreo, logs)
- Backup manual de la base de datos con rotacion

### Artesanos AI
- Chat con inteligencia artificial (Google Gemini)
- Contexto real de facturas, proveedores y sucursales
- Preguntas sugeridas para consultas rapidas
- Solo accesible para administradores

## Tecnologias

| Capa | Tecnologia |
|------|------------|
| Backend | Python 3.9+ / Flask 3.0 |
| ORM | SQLAlchemy + Flask-SQLAlchemy |
| Base de datos | MySQL 8 (produccion) / MariaDB via XAMPP (local) |
| Autenticacion | Flask-Login + Werkzeug Security (scrypt) |
| Migraciones | Flask-Migrate |
| Frontend | HTML5 + CSS3 + JavaScript + Bootstrap 5.3 |
| IA | Google Gemini 3.8 Flash |
| Emails | SMTP via Gmail |
| Excel | openpyxl |
| Monitoreo | psutil |
| Deploy | AWS Lightsail + Nginx + Gunicorn + systemd |
| HTTPS | Let's Encrypt + Certbot |
| Dominio | DuckDNS |

## Instalacion local

### Requisitos previos
- Python 3.9 o superior
- MySQL o MariaDB (XAMPP recomendado para Windows)
- Git

### Pasos

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/danielQuintanillaPanamagua/artesanos-control.git
   cd artesanos-control 
python -m venv venv
Crear y activar el entorno virtual
.\venv\Scripts\Activate.ps1
Instalar dependencias
pip install -r requirements.txt
onfigurar el archivo .env (copiar de .env.example)
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
Crear la base de datos (en MySQL/XAMPP)
CREATE DATABASE artesanos_control CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
Crear las tablas y datos iniciales
python crear_admin.py
Arrancar el servidor
python run.py
Abrir en el navegador
http://127.0.0.1:5000
Credenciales por defecto
Rol    Usuario    Contrasena
Admin    admin    (ver crear_admin.py)
IMPORTANTE: cambiar la contrasena del admin despues del primer login.
Estructura del proyecto
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
│   ├── services/                # Logica de negocio
│   │   ├── validacion.py
│   │   ├── email_service.py
│   │   ├── system_service.py
│   │   ├── excel_service.py
│   │   └── artesanos_ai.py
│   ├── templates/               # Templates Jinja2
│   ├── static/                  # CSS, JS, imagenes
│   └── instance/                # SQLite (solo dev)
├── migrations/                  # Flask-Migrate
├── backups/                     # Backups de BD (gitignored)
├── .env                         # Variables de entorno (NO en git)
├── .env.example                 # Plantilla
├── .gitignore
├── requirements.txt
├── crear_admin.py
└── run.py
Deploy a produccion
Arquitectura
Cliente → HTTPS → Nginx (443) → Gunicorn (socket) → Flask → MySQL
Servidor
Proveedor: AWS Lightsail (1 GB RAM, 2 vCPU)

OS: Ubuntu 24.04 LTS

Region: US East (Ohio)

Servicios
Gunicorn: /etc/systemd/system/artesanos.service (1 worker + 4 threads)

Nginx: /etc/nginx/sites-available/artesanos (proxy inverso)

SSL: Let's Encrypt con renovacion automatica via Certbot

Actualizar produccion
ssh -i /ruta/a/tu/llave.pem ubuntu@IP_DEL_SERVIDOR
cd /home/ubuntu/artesanos-control
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart artesanos.service
Backup de la base de datos
mysqldump -u artesanos -pArtesanos2026 --no-tablespaces artesanos_control > backup_$(date +%Y%m%d).sql
O desde el panel: /admin/configuracion → "Crear backup ahora"

Variables de entorno
Variable    Descripcion    Ejemplo
FLASK_SECRET_KEY    Clave secreta de Flask    generar_con_secrets
SQLALCHEMY_DATABASE_URI    URI de conexion a MySQL    mysql+pymysql://user:pass@host/db
FLASK_ENV    Entorno de Flask    development / production
FLASK_DEBUG    Modo debug    True / False
SMTP_HOST    Servidor SMTP    smtp.gmail.com
SMTP_PORT    Puerto SMTP    587
SMTP_USER    Usuario SMTP    correo@gmail.com
SMTP_PASSWORD    Contrasena de aplicacion    16 caracteres
GEMINI_API_KEY    API key de Google Gemini    AIza...
Contribucion
Las ramas siguen el patron:

main → rama estable

daniel-pre-production → rama de desarrollo pre-produccion

feature/xxx → nuevas funcionalidades

Licencia
Proyecto privado de ARTESANOS PIZZERIA. Todos los derechos reservados.

Ultima actualizacion: Octubre 2026

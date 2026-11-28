# 🛠️ Guía de instalación — ARTESANOS CONTROL

Esta guía explica cómo instalar **ARTESANOS CONTROL** desde cero, de dos formas:

- **Parte A — Instalación local** (tu computadora, para probar o desarrollar).
- **Parte B — Instalación en un servidor** (Ubuntu, con dominio y HTTPS, para uso real).

> Todos los comandos de esta guía fueron probados en una instalación limpia. Los archivos de ejemplo de la Parte B (systemd y Nginx) son una **plantilla**: ajusta rutas, usuario y dominio a tu servidor.

---

## 📋 Índice

1. [Qué necesitas](#1-qué-necesitas)
2. [Parte A: instalación local](#2-parte-a-instalación-local)
3. [Parte B: instalación en servidor](#3-parte-b-instalación-en-servidor-ubuntu)
4. [Configurar correo (SMTP) y la IA (Gemini)](#4-configurar-correo-smtp-y-la-ia-gemini)
5. [Primer uso del sistema](#5-primer-uso-del-sistema)
6. [Actualizar a una versión nueva](#6-actualizar-a-una-versión-nueva)
7. [Copias de seguridad](#7-copias-de-seguridad)
8. [Problemas frecuentes](#8-problemas-frecuentes)

---

## 1. Qué necesitas

| Requisito | Detalle |
|-----------|---------|
| Python | 3.9 o superior |
| Base de datos | MySQL 8 o MariaDB (en Windows, [XAMPP](https://www.apachefriends.org/) es lo más fácil) |
| Git | Para descargar el código |
| Internet | El navegador necesita internet para cargar Bootstrap desde un CDN; el servidor lo necesita para la IA y el correo |
| (Opcional) Cuenta de Gmail | Para enviar correos de recuperación de contraseña (usa una *contraseña de aplicación*) |
| (Opcional) API key de Google Gemini | Para el asistente **Artesanos AI** |

> El sistema **funciona sin** Gmail y sin Gemini: solo quedan desactivados la recuperación de contraseña por correo y el asistente de IA.

---

## 2. Parte A: instalación local

### Paso 1. Descargar el código

```bash
git clone https://github.com/DanielQuintanillaPaniagua/artesanos-control.git
cd artesanos-control
```

### Paso 2. Crear y activar el entorno virtual

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> Si PowerShell dice que la ejecución de scripts está deshabilitada, ejecuta una vez
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y repite el comando. También puedes usar **CMD** con `venv\Scripts\activate`.

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

Sabrás que está activo porque verás `(venv)` al inicio de la línea.

### Paso 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

### Paso 4. Crear la base de datos

1. En XAMPP, abre el panel y pulsa **Start** en **MySQL**.
2. Abre `http://localhost/phpmyadmin` → pestaña **SQL** y ejecuta:

```sql
CREATE DATABASE artesanos_control CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

(O desde la terminal de MySQL, con el mismo comando.)

### Paso 5. Configurar las variables de entorno

Copia la plantilla y edítala:

```bash
# Windows (PowerShell)
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Abre `.env` y, como mínimo, revisa estas líneas:

```env
FLASK_SECRET_KEY=pon_aqui_una_clave_larga_y_aleatoria
SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:@127.0.0.1/artesanos_control
FLASK_ENV=development
FLASK_DEBUG=True
```

- `FLASK_SECRET_KEY`: una cadena larga y aleatoria. Puedes generarla con:
  `python -c "import secrets; print(secrets.token_hex(32))"`
- `SQLALCHEMY_DATABASE_URI`: en XAMPP el usuario es `root` y **sin contraseña** (`root:@`). Si tu MySQL tiene contraseña, escríbela después de los dos puntos: `root:MI_CLAVE@`.
- `FLASK_ENV=development`: **obligatorio en local** (en `production` el sistema exige HTTPS y un dominio, ver [Problemas frecuentes](#8-problemas-frecuentes)).

### Paso 6. Crear las tablas y los datos iniciales

```bash
python crear_admin.py
```

Este script es seguro de repetir. Crea:

- Todas las tablas de la base de datos.
- Los tipos de documento base (FCC, FC, Nota de envío, Otros).
- Una sucursal base llamada **Owner**.
- Las **21 categorías** de gasto iniciales.
- El usuario administrador.

Al terminar muestra las credenciales (ver [Primer uso](#5-primer-uso-del-sistema)).

### Paso 7. Arrancar el servidor

```bash
python run.py
```

### Paso 8. Abrir el sistema

Entra a <http://127.0.0.1:5000> e inicia sesión.

Para detener el servidor usa `Ctrl + C`. Para volver a arrancarlo otro día:

```powershell
cd ruta\a\artesanos-control
.\venv\Scripts\Activate.ps1
python run.py
```

---

## 3. Parte B: instalación en servidor (Ubuntu)

Esta parte asume un servidor **Ubuntu 22.04 / 24.04** (por ejemplo, AWS Lightsail), un **dominio** que apunta a la IP del servidor y acceso por SSH con un usuario con `sudo` (en los ejemplos, `ubuntu`).

> ⚠️ **En producción el HTTPS es obligatorio.** Con `FLASK_ENV=production` las cookies de sesión se marcan como *Secure*: si entras por `http://`, el navegador no las guarda y **no podrás iniciar sesión**. Por eso esta guía incluye el certificado de Let's Encrypt.

### Paso 1. Instalar los paquetes del sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx mysql-server certbot python3-certbot-nginx
```

### Paso 2. Crear la base de datos y su usuario

```bash
sudo mysql
```

Dentro de MySQL (cambia `TU_PASSWORD_SEGURA`):

```sql
CREATE DATABASE artesanos_control CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'artesanos'@'localhost' IDENTIFIED BY 'TU_PASSWORD_SEGURA';
GRANT ALL PRIVILEGES ON artesanos_control.* TO 'artesanos'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> 🔑 Usa una contraseña **sin** los caracteres `@ : / # ? %`. Van dentro de la dirección de conexión y la romperían (también el backup desde el panel).

### Paso 3. Descargar el código e instalar dependencias

```bash
cd /home/ubuntu
git clone https://github.com/DanielQuintanillaPaniagua/artesanos-control.git
cd artesanos-control
git checkout main

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

> `gunicorn` es el servidor que usa producción y **no** viene en `requirements.txt`, por eso se instala aparte.

### Paso 4. Configurar `.env` para producción

```bash
cp .env.example .env
nano .env
```

Valores mínimos:

```env
FLASK_SECRET_KEY=GENERA_UNA_CLAVE_LARGA_Y_ALEATORIA
FLASK_ENV=production
FLASK_DEBUG=False
SQLALCHEMY_DATABASE_URI=mysql+pymysql://artesanos:TU_PASSWORD_SEGURA@localhost/artesanos_control

# OBLIGATORIO en produccion: tu dominio (sin https:// ni barras)
SERVER_NAME=tu-dominio.com
PREFERRED_URL_SCHEME=https
```

Genera la clave con `python3 -c "import secrets; print(secrets.token_hex(32))"`.

> ⚠️ **`SERVER_NAME` es obligatorio.** Si lo omites, el sistema usará un dominio de ejemplo y el servidor responderá *404* a tu dominio real.

Protege el archivo:

```bash
chmod 600 .env
```

### Paso 5. Crear las tablas y el usuario inicial

```bash
python crear_admin.py
```

### Paso 6. Crear el servicio (systemd)

Crea el archivo del servicio:

```bash
sudo nano /etc/systemd/system/artesanos.service
```

Contenido de **ejemplo** (ajusta usuario y rutas):

```ini
[Unit]
Description=ARTESANOS CONTROL (Gunicorn)
After=network.target mysql.service

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/artesanos-control
ExecStart=/home/ubuntu/artesanos-control/venv/bin/gunicorn --workers 1 --threads 4 --umask 007 --bind unix:/run/artesanos/artesanos.sock run:app
RuntimeDirectory=artesanos
Restart=always

[Install]
WantedBy=multi-user.target
```

Actívalo:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now artesanos.service
sudo systemctl status artesanos.service
```

Debe decir `active (running)`. Si falla: `sudo journalctl -u artesanos.service -n 50`.

> Se usa **1 worker con 4 hilos** a propósito: el servidor de 1 GB de RAM es pequeño y el límite de intentos de login se guarda en memoria.

### Paso 7. Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/artesanos
```

Contenido de **ejemplo** (cambia `tu-dominio.com`):

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    # El sistema acepta Excel de hasta 5 MB; Nginx por defecto solo deja 1 MB
    client_max_body_size 6m;

    location / {
        proxy_pass http://unix:/run/artesanos/artesanos.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

Actívalo:

```bash
sudo ln -s /etc/nginx/sites-available/artesanos /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Paso 8. Abrir los puertos y activar HTTPS

En el firewall del proveedor (en Lightsail: pestaña **Networking**) abre los puertos **80** y **443**. Si usas `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Luego pide el certificado (cambia el dominio y pon tu correo cuando lo pida):

```bash
sudo certbot --nginx -d tu-dominio.com
```

Certbot modifica Nginx para usar HTTPS y deja la renovación automática. Puedes comprobarla con `sudo certbot renew --dry-run`.

### Paso 9. Comprobar

Abre `https://tu-dominio.com` e inicia sesión. Si algo falla, revisa los registros:

```bash
sudo journalctl -u artesanos.service -n 50
sudo tail -n 50 /var/log/nginx/error.log
```

---

## 4. Configurar correo (SMTP) y la IA (Gemini)

Ambos son opcionales. Se configuran en el `.env` y **requieren reiniciar** el sistema para tomar efecto.

### Correo para recuperar contraseñas (Gmail)

1. En tu cuenta de Google activa la **verificación en dos pasos**.
2. Crea una **contraseña de aplicación** (Cuenta de Google → Seguridad → Contraseñas de aplicaciones). Te dará 16 caracteres.
3. Completa en `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=la_contrasena_de_aplicacion_de_16_caracteres
SMTP_FROM=Artesanos Control <tu_correo@gmail.com>
```

4. Cada usuario debe tener su **correo registrado** en el sistema para poder recuperar su contraseña.
5. Comprueba el envío en *Administración → Configuración* (sección de correo).

### Artesanos AI (Google Gemini)

1. Crea una API key en <https://aistudio.google.com/apikey>.
2. Agrégala al `.env`:

```env
GEMINI_API_KEY=tu_api_key
```

3. Reinicia y prueba en **Artesanos AI** con una pregunta como: *"¿Cuánto se gastó en Comida este mes?"*

---

## 5. Primer uso del sistema

### Credenciales iniciales

`crear_admin.py` crea este usuario:

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Owner | `owner` | `artesanos2026` |

> ⚠️ **Cambia la contraseña inmediatamente** después del primer inicio de sesión (menú **Mi perfil**).

### Orden recomendado de configuración

1. **Sucursales**: crea las sucursales reales del negocio (menú *Sucursales*). Puedes desactivar o ignorar la sucursal base "Owner".
2. **Usuarios**: crea los supervisores y empleados y asígnales su sucursal (*Administración → Usuarios*).
3. **Catálogo** (*Administración → Categorías, proveedores y tipos de documento*):
   - Revisa las categorías iniciales y crea las que falten.
   - Crea los **tipos de documento** que usa el negocio (ejemplo: `CCF (Crédito Fiscal)`).
   - Desactiva lo que ya no se use (no se borra: las facturas anteriores conservan sus datos).
4. **Proveedores**: se pueden crear desde el formulario de factura con el botón **+**.
5. (Opcional) **Importar** facturas históricas desde Excel (*Administración → Importar*).

### Roles

| Rol | Qué puede hacer |
|-----|-----------------|
| **Owner** | Todo: ver todas las sucursales, registrar y corregir facturas, administrar usuarios, catálogo y configuración |
| **Supervisor** | Gestionar usuarios, facturas y reportes de **su** sucursal |
| **Empleado** | Registrar y consultar facturas de **su** sucursal |

---

## 6. Actualizar a una versión nueva

**En local:**

```bash
git pull
.\venv\Scripts\Activate.ps1        # o: source venv/bin/activate
pip install -r requirements.txt
python run.py
```

**En el servidor:**

```bash
cd /home/ubuntu/artesanos-control
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python crear_admin.py        # crea tablas nuevas si la version las trae (no borra nada)
sudo systemctl restart artesanos.service
```

- `crear_admin.py` y `run.py` solo **crean tablas nuevas**; no modifican las existentes. Si una versión cambia columnas de una tabla que ya existe, el equipo de desarrollo debe indicarlo en las notas de la versión.
- Después de actualizar, pide a los usuarios que recarguen con `Ctrl + F5` para limpiar el caché del navegador.

---

## 7. Copias de seguridad

**Desde el sistema (Owner):** *Administración → Configuración* → **Crear backup ahora**. Guarda el archivo en la carpeta `backups/` del proyecto y conserva los últimos 7. Requiere que `mysqldump` esté instalado (viene con MySQL).

**Desde la terminal** (pedirá la contraseña):

```bash
mysqldump -u artesanos -p --no-tablespaces artesanos_control > backup_$(date +%Y%m%d).sql
```

**Restaurar** un backup:

```bash
mysql -u artesanos -p artesanos_control < backup_AAAAMMDD.sql
```

> 💾 Descarga copias fuera del servidor con regularidad. Un backup guardado solo en el mismo servidor se pierde si el servidor se pierde.

---

## 8. Problemas frecuentes

| Problema | Causa y solución |
|----------|------------------|
| `FLASK_SECRET_KEY no configurada` | Falta el archivo `.env` o la variable. Copia `.env.example` a `.env` y complétalo. |
| `Can't connect to MySQL server` | MySQL no está encendido (en XAMPP, pulsa **Start**) o la URI de `.env` es incorrecta. |
| `Unknown database 'artesanos_control'` | No creaste la base de datos (Paso 4 local / Paso 2 servidor). |
| `Access denied for user` | Usuario o contraseña de la URI incorrectos. |
| `ModuleNotFoundError` | El entorno virtual no está activo o no instalaste las dependencias (`pip install -r requirements.txt`). |
| En producción, **el login no avanza** o vuelve a la pantalla de inicio de sesión | Estás entrando por `http://` en vez de `https://`. En producción las cookies exigen HTTPS. Activa el certificado (Paso 8). |
| En producción, **404** en todo el sitio | Falta `SERVER_NAME=tu-dominio.com` en `.env`, o no coincide con el dominio. |
| **502 Bad Gateway** en Nginx | El servicio no está corriendo: `sudo systemctl status artesanos.service` y revisa `journalctl`. |
| No se pueden importar archivos Excel grandes | Falta `client_max_body_size 6m;` en Nginx. El sistema acepta hasta 5 MB. |
| Estilos o botones se ven rotos | Caché del navegador: `Ctrl + F5`. Verifica también que el equipo tenga internet (Bootstrap se carga de un CDN). |
| El backup desde el panel falla | `mysqldump` no está instalado o la contraseña de la base de datos tiene caracteres como `@ : /`. |
| Artesanos AI no responde | Revisa `GEMINI_API_KEY` en `.env` y que el servidor tenga salida a internet. |
| No llegan los correos de recuperación | Revisa las variables `SMTP_*` y que uses una **contraseña de aplicación** de Gmail, no tu contraseña normal. |

---

📘 Más información en el [README](README.md) y en la documentación de la API ([API_DOCS.md](API_DOCS.md)).
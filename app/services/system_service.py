import os
import sys
import platform
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

import flask
from sqlalchemy import text


def get_system_info():
    """Informacion del sistema (Python, Flask, MySQL, uptime)."""
    info = {
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'os': f"{platform.system()} {platform.release()}",
        'machine': platform.machine(),
        'hostname': platform.node(),
    }

    # Version de MySQL
    try:
        from app import db
        result = db.session.execute(text("SELECT VERSION()")).scalar()
        info['mysql_version'] = result
    except Exception:
        info['mysql_version'] = 'No disponible'

    # Uptime (desde cuando arranco el proceso)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        uptime_seconds = int(datetime.now().timestamp() - process.create_time())
        dias = uptime_seconds // 86400
        horas = (uptime_seconds % 86400) // 3600
        minutos = (uptime_seconds % 3600) // 60
        info['uptime'] = f"{dias}d {horas}h {minutos}m"
    except ImportError:
        info['uptime'] = 'psutil no instalado'
    except Exception:
        info['uptime'] = 'No disponible'

    return info


def get_server_status():
    """Estado del servidor (RAM, disco, SWAP)."""
    status = {
        'ram_total': 'N/D',
        'ram_used': 'N/D',
        'ram_percent': 0,
        'disk_total': 'N/D',
        'disk_used': 'N/D',
        'disk_percent': 0,
        'swap_total': 'N/D',
        'swap_used': 'N/D',
        'swap_percent': 0,
    }

    # RAM + SWAP con psutil
    try:
        import psutil

        mem = psutil.virtual_memory()
        status['ram_total'] = _format_bytes(mem.total)
        status['ram_used'] = _format_bytes(mem.used)
        status['ram_percent'] = mem.percent
        status['ram_available'] = _format_bytes(mem.available)

        swap = psutil.swap_memory()
        status['swap_total'] = _format_bytes(swap.total)
        status['swap_used'] = _format_bytes(swap.used)
        status['swap_percent'] = swap.percent
    except ImportError:
        pass

    # Disco
    try:
        disk = shutil.disk_usage('/')
        status['disk_total'] = _format_bytes(disk.total)
        status['disk_used'] = _format_bytes(disk.used)
        status['disk_percent'] = int((disk.used / disk.total) * 100)
    except Exception:
        pass

    return status


def _format_bytes(bytes_val):
    """Convierte bytes a formato legible."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def get_backup_dir():
    """Devuelve la carpeta de backups (crea si no existe)."""
    base = Path(__file__).resolve().parent.parent.parent  # raiz del proyecto
    backup_dir = base / 'backups'
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def create_backup():
    """Crea un backup de la BD con mysqldump. Devuelve (ok, path_o_error)."""
    from dotenv import load_dotenv
    load_dotenv()

    uri = os.getenv('SQLALCHEMY_DATABASE_URI', '')

    if not uri.startswith('mysql'):
        return False, 'Solo se soporta MySQL'

    # Parsear: mysql+pymysql://user:pass@host/dbname
    try:
        resto = uri.replace('mysql+pymysql://', '').replace('mysql://', '')
        credenciales, resto2 = resto.split('@', 1)
        if ':' in credenciales:
            user, password = credenciales.split(':', 1)
        else:
            user = credenciales
            password = ''
        host_db = resto2.split('/')
        host = host_db[0]
        dbname = host_db[1] if len(host_db) > 1 else 'artesanos_control'
    except Exception as e:
        return False, f'Error parseando URI: {e}'

    # Detectar mysqldump segun SO
    if platform.system() == 'Windows':
        candidatos = [
            r'C:\xampp\mysql\bin\mysqldump.exe',
            r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
        ]
        mysqldump = next((c for c in candidatos if os.path.exists(c)), 'mysqldump')
    else:
        mysqldump = 'mysqldump'

    # Generar nombre del archivo
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{dbname}_{timestamp}.sql'
    filepath = backup_dir / filename

    # Armar comando
    # SEGURIDAD: NO pasar la password por linea de comandos (visible en ps).
    # Se usa la variable de entorno MYSQL_PWD, que no aparece en ps.
    cmd = [mysqldump, f'-u{user}']

    cmd.extend([
        '--no-tablespaces',
        '--single-transaction',
        '--routines',
        '--triggers',
    ])

    # Solo agregar host si NO es localhost/127.0.0.1
    if host and host not in ('localhost', '127.0.0.1'):
        cmd.append(f'-h{host}')

    cmd.append(dbname)

    # Preparar entorno con MYSQL_PWD (solo si hay password)
    env = os.environ.copy()
    if password:
        env['MYSQL_PWD'] = password

    # Ejecutar
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                timeout=120,
                text=True,
                env=env,
            )

        if result.returncode != 0:
            # Borrar el archivo vacio
            if filepath.exists() and filepath.stat().st_size == 0:
                filepath.unlink()
            return False, f'Error mysqldump: {result.stderr.strip()}'

        if not filepath.exists() or filepath.stat().st_size == 0:
            return False, 'El backup quedo vacio. Verifica credenciales de MySQL.'

        _rotar_backups(backup_dir, keep=7)
        return True, str(filepath)

    except FileNotFoundError:
        return False, 'mysqldump no encontrado. Verifica la ruta.'
    except subprocess.TimeoutExpired:
        return False, 'El backup tardo mas de 2 minutos (timeout)'
    except Exception as e:
        return False, f'Error inesperado: {e}'

def _rotar_backups(backup_dir, keep=7):
    """Borra los backups mas viejos, manteniendo los ultimos N."""
    archivos = sorted(backup_dir.glob('*.sql'), key=lambda p: p.stat().st_mtime, reverse=True)
    for viejo in archivos[keep:]:
        try:
            viejo.unlink()
        except Exception:
            pass


def get_recent_logs(lines=50):
    """Lee las ultimas lineas del log. Devuelve lista de strings."""
    log_paths = [
        Path('/home/ubuntu/artesanos-control/artesanos.log'),
        Path(__file__).resolve().parent.parent.parent / 'artesanos.log',
        Path('/var/log/nginx/error.log'),
    ]

    for p in log_paths:
        if p.exists():
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    all_lines = f.readlines()
                    return [l.rstrip('\n') for l in all_lines[-lines:]]
            except Exception:
                continue
    return ['(no hay logs disponibles)']


def get_smtp_status():
    """Verifica si el SMTP esta configurado."""
    from dotenv import load_dotenv
    load_dotenv()

    host = os.getenv('SMTP_HOST', '')
    user = os.getenv('SMTP_USER', '')

    return {
        'configurado': bool(host and user),
        'host': host or '(no configurado)',
        'user': user or '(no configurado)',
    }


def limpiar_tokens_expirados():
    """Elimina tokens de recuperacion expirados o usados."""
    from app import db
    from app.models.user import PasswordResetToken
    from datetime import timezone

    ahora = datetime.now(timezone.utc)

    # Borrar expirados
    expirados = PasswordResetToken.query.filter(
        PasswordResetToken.expira < ahora
    ).delete()

    # Borrar usados (hace mas de 1 dia)
    from datetime import timedelta
    hace_un_dia = ahora - timedelta(days=1)
    usados = PasswordResetToken.query.filter(
        PasswordResetToken.usado == True,
        PasswordResetToken.created_at < hace_un_dia
    ).delete()

    db.session.commit()

    return expirados + usados

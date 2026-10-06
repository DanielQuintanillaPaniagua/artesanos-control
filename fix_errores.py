"""
Script de un solo uso: reemplaza todos los `error: str(e)` por
un mensaje generico + logging del error real.
"""
import re
from pathlib import Path


# Archivos a procesar
ARCHIVOS = [
    "app/routes/categorias_api.py",
    "app/routes/dashboard_api.py",
    "app/routes/proveedores_api.py",
    "app/routes/reportes_api.py",
    "app/routes/sucursales_api.py",
    "app/routes/usuarios_api.py",
]

# Patron a buscar
PATRON_BUSCAR = r"return jsonify\(\{'success': False, 'error': str\(e\)\}\), 500"

# Reemplazo (con logging)
REEMPLAZO = """current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500"""


def procesar_archivo(path):
    p = Path(path)
    if not p.exists():
        print(f"  SKIP: {path} (no existe)")
        return 0

    contenido = p.read_text(encoding='utf-8')
    original = contenido

    # Reemplazar
    contenido, count = re.subn(PATRON_BUSCAR, REEMPLAZO, contenido)

    if count == 0:
        print(f"  {path}: sin cambios")
        return 0

    # Verificar que current_app este importado
    if "current_app" not in contenido.split('\n')[0:15][0]:
        # Agregar import si no esta
        if "from flask import" in contenido:
            # Agregar a la linea de imports de flask
            contenido = re.sub(
                r"from flask import ([^\n]+)",
                lambda m: f"from flask import {m.group(1)}, current_app"
                if "current_app" not in m.group(1)
                else m.group(0),
                contenido,
                count=1,
            )
        else:
            # Agregar linea nueva
            contenido = "from flask import current_app\n" + contenido

    p.write_text(contenido, encoding='utf-8')
    print(f"  {path}: {count} reemplazos")
    return count


def main():
    print("=" * 60)
    print("REEMPLAZANDO str(e) POR MENSAJE GENERICO + LOGGING")
    print("=" * 60)

    total = 0
    for archivo in ARCHIVOS:
        total += procesar_archivo(archivo)

    print("=" * 60)
    print(f"TOTAL: {total} reemplazos")
    print("=" * 60)


if __name__ == '__main__':
    main()

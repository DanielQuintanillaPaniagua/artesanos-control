import os
import time
import logging
from google import genai
from datetime import date, datetime, timedelta

from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.proveedor import Proveedor
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria
from app.models.user import User

logger = logging.getLogger(__name__)

# ============================================================
# Configuracion de Gemini (Nuevo SDK google-genai)
# ============================================================
# gemini-2.5-flash: modelo estable y rápido (recomendado)
# gemini-3.8-flash: modelo más nuevo, pero a veces saturado (503)
MODEL_NAME = "gemini-2.5-flash"


def _get_client():
    """Crea el cliente de Gemini con la API key del .env."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada en el .env")
    return genai.Client(api_key=api_key)


def _llamar_gemini_con_reintentos(cliente, prompt, max_intentos=3):
    """
    Llama a Gemini con reintentos automaticos en caso de 503 (alta demanda).
    Backoff exponencial: 2s, 4s entre intentos.
    """
    ultimo_error = None

    for intento in range(1, max_intentos + 1):
        try:
            return cliente.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
        except Exception as e:
            err_str = str(e).lower()
            ultimo_error = e

            # Solo reintentar en errores transitorios del servidor
            es_transitorio = any(code in err_str for code in [
                '503', '500', '429', 'unavailable', 'overloaded', 'timeout'
            ])

            if es_transitorio and intento < max_intentos:
                espera = 2 * intento  # 2s, 4s
                logger.warning(
                    f"Gemini fallo (intento {intento}/{max_intentos}): {str(e)[:100]}. "
                    f"Reintentando en {espera}s..."
                )
                time.sleep(espera)
                continue

            # Error no transitorio o ultimo intento: lanzar
            raise

    # Si llegamos aca, se agotaron los intentos
    raise ultimo_error or Exception("Gemini fallo despues de multiples intentos")


# ============================================================
# Recopilar contexto del negocio (AMPLIADO)
# ============================================================
def _recopilar_contexto(sucursal_id=None):
    """Recopila resumen de datos de Artesanos Control para darselo a Gemini."""
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    base = Factura.query
    if sucursal_id:
        base = base.filter(Factura.sucursal_id == sucursal_id)

    total_facturas = base.count()
    facturas_mes = base.filter(Factura.fecha >= inicio_mes).all()
    total_facturas_mes = len(facturas_mes)
    monto_mes = sum((f.total_factura or 0) for f in facturas_mes)

    validadas_mes = sum(1 for f in facturas_mes if f.estado == 'Validada')
    observadas_mes = sum(1 for f in facturas_mes if f.estado == 'Observada')

    # --- Datos de Sucursales y Usuarios (AMPLIADO) ---
    if sucursal_id:
        sucursales_db = Sucursal.query.filter_by(id=sucursal_id).all()
        total_sucursales = len(sucursales_db)
    else:
        sucursales_db = Sucursal.query.order_by(Sucursal.nombre).all()
        total_sucursales = sum(1 for s in sucursales_db if s.estado == 'Activa')

    # Lista de nombres de sucursales
    sucursales_nombres = ", ".join([f"{s.nombre} ({s.estado})" for s in sucursales_db])

    # Conteo de usuarios
    query_users = User.query.filter_by(estado='Activo')
    if sucursal_id:
        query_users = query_users.filter_by(sucursal_id=sucursal_id)
    
    usuarios_activos = query_users.all()
    total_usuarios = len(usuarios_activos)
    
    # Desglose de usuarios por rol
    owners = sum(1 for u in usuarios_activos if u.rol == 'owner')
    supervisores = sum(1 for u in usuarios_activos if u.rol == 'supervisor')
    empleados = sum(1 for u in usuarios_activos if u.rol == 'empleado')
    
    total_proveedores = Proveedor.query.filter_by(estado='Activo').count()

    # --- Desglose por sucursal (ultimo mes) ---
    sucursales_info = []
    if sucursal_id:
        sucursales_query = Sucursal.query.filter_by(id=sucursal_id).all()
    else:
        sucursales_query = Sucursal.query.order_by(Sucursal.nombre).all()

    for s in sucursales_query:
        f_suc = [f for f in facturas_mes if f.sucursal_id == s.id]
        if f_suc:
            monto = sum((f.total_factura or 0) for f in f_suc)
            val = sum(1 for f in f_suc if f.estado == 'Validada')
            obs = sum(1 for f in f_suc if f.estado == 'Observada')
            sucursales_info.append(
                f"  - {s.nombre}: {len(f_suc)} facturas, ${monto:.2f} "
                f"({val} validadas, {obs} observadas)"
            )
    sucursales_txt = "\n".join(sucursales_info) or "  - Sin datos"

    # --- Top proveedores por monto (mes actual) ---
    proveedores_mes = {}
    for f in facturas_mes:
        if f.proveedor:
            nombre = f.proveedor.nombre
            proveedores_mes[nombre] = proveedores_mes.get(nombre, 0) + (f.total_factura or 0)

    top_proveedores = sorted(proveedores_mes.items(), key=lambda x: x[1], reverse=True)[:5]
    proveedores_txt = "\n".join(
        [f"  - {n}: ${m:.2f}" for n, m in top_proveedores]
    ) or "  - Sin datos"

    # --- Desglose por categoria (mes actual) ---
    categorias_mes = {}
    for f in facturas_mes:
        for d in f.detalles:
            cid = d.categoria_id
            categorias_mes[cid] = categorias_mes.get(cid, 0) + (d.monto or 0)

    cats_info = []
    for cid, monto in sorted(categorias_mes.items(), key=lambda x: x[1], reverse=True)[:10]:
        cat = db.session.get(Categoria, cid)
        if cat:
            cats_info.append(f"  - {cat.nombre}: ${monto:.2f}")
    categorias_txt = "\n".join(cats_info) or "  - Sin datos"

    # --- Facturas observadas (mes actual) ---
    observadas = [f for f in facturas_mes if f.estado == 'Observada'][:10]
    observadas_txt = "\n".join([
        f"  - #{f.numero_factura} ({f.fecha.strftime('%d/%m/%Y')}): ${f.total_factura:.2f}"
        + (f" - {f.observacion[:80]}" if f.observacion else "")
        for f in observadas
    ]) or "  - Ninguna"

    # --- Ultimas 10 facturas ---
    ultimas = base.order_by(Factura.fecha.desc(), Factura.id.desc()).limit(10).all()
    ultimas_txt = "\n".join([
        f"  - #{f.numero_factura} - {f.proveedor.nombre if f.proveedor else '?'} "
        f"- ${f.total_factura:.2f} ({f.estado}) - {f.fecha.strftime('%d/%m/%Y')}"
        for f in ultimas
    ]) or "  - Sin datos"

    contexto = f"""DATOS ACTUALES DE ARTESANOS PIZZERIA (usar SOLO esta informacion):

Fecha de hoy: {hoy.strftime('%d/%m/%Y')}
Periodo del reporte: mes actual (desde {inicio_mes.strftime('%d/%m/%Y')})

ESTRUCTURA DEL NEGOCIO:
- Sucursales registradas: {sucursales_nombres}
- Total de usuarios activos: {total_usuarios} (Owners: {owners}, Supervisores: {supervisores}, Empleados: {empleados})
- Total de proveedores activos: {total_proveedores}

RESUMEN DE FACTURAS GENERAL:
- Total de facturas historicas: {total_facturas}
- Facturas del mes actual: {total_facturas_mes}
- Monto total del mes: ${monto_mes:.2f}
- Facturas validadas este mes: {validadas_mes}
- Facturas observadas este mes: {observadas_mes}

DESEMPENO POR SUCURSAL (mes actual):
{sucursales_txt}

TOP 5 PROVEEDORES POR MONTO (mes actual):
{proveedores_txt}

DESGLOSE POR CATEGORIA (mes actual):
{categorias_txt}

FACTURAS OBSERVADAS (mes actual):
{observadas_txt}

ULTIMAS 10 FACTURAS REGISTRADAS:
{ultimas_txt}
"""
    return contexto


# ============================================================
# Funcion principal
# ============================================================
def preguntar_a_artesanos_ai(pregunta_usuario, historial=None, sucursal_id=None):
    """Envia una pregunta a Gemini con el contexto de Artesanos Control."""

    try:
        cliente = _get_client()
        contexto = _recopilar_contexto(sucursal_id=sucursal_id)

        prompt = f"""Eres "Artesanos AI", el asistente inteligente del sistema "Artesanos Control" de ARTESANOS PIZZERIA (una empresa salvadorena).

Tu personalidad:
- Profesional, conciso y servicial.
- Hablas en espanol.
- Das respuestas claras y directas.
- Usas emojis con moderacion para hacer la respuesta mas visual (📊, 💰, 📦, ⚠️, 🏪).

REGLAS ESTRICTAS:
1. SOLO usa los datos del CONTEXTO de abajo para responder.
2. Si la pregunta no se puede responder con esos datos, dilo amablemente.
3. NUNCA inventes cifras, nombres o datos.
4. Si mencionas varias cosas, usa listas numeradas o con vinetas.
5. Se conciso: maximo 180 palabras por respuesta.
6. Si el usuario pregunta por una sucursal especifica, filtra los datos por esa sucursal.
7. Los montos son en dolares (USD).
8. Tienes permitido decir cuantos usuarios/empleados hay si te lo preguntan usando la seccion ESTRUCTURA DEL NEGOCIO.

CONTEXTO ACTUAL DE ARTESANOS CONTROL:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta_usuario}

RESPUESTA:"""

        # Llamar con reintentos automaticos
        respuesta = _llamar_gemini_con_reintentos(cliente, prompt)

        return {
            'ok': True,
            'respuesta': respuesta.text
        }

    except ValueError as e:
        # Error de configuracion (ej: falta API Key). Seguro de mostrar.
        return {'ok': False, 'error': str(e)}
    except Exception as e:
        # Cualquier otro error: loggear y devolver mensaje generico
        logger.exception("Error en Artesanos AI")

        err_str = str(e).lower()
        if "model" in err_str and "not found" in err_str:
            return {
                'ok': False,
                'error': "El modelo de IA configurado no esta disponible. Contacta al administrador."
            }
        if "503" in err_str or "unavailable" in err_str:
            return {
                'ok': False,
                'error': "El servicio de IA esta experimentando alta demanda. Intenta de nuevo en unos segundos."
            }

        return {
            'ok': False,
            'error': "Lo siento, tuve un problema al procesar tu consulta. Intenta de nuevo en unos minutos."
        }
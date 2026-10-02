import os
import google.generativeai as genai
from datetime import date, datetime, timedelta
from sqlalchemy import func

from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.proveedor import Proveedor
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria
from app.models.user import User


# ============================================================
# Configuracion de Gemini
# ============================================================
MODEL_NAME = "gemini-3.8-flash"


def _get_model():
    """Crea el modelo de Gemini con la API key del .env."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada en el .env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


# ============================================================
# Recopilar contexto del negocio
# ============================================================
def _recopilar_contexto(sucursal_id=None):
    """Recopila resumen de datos de Artesanos Control para darselo a Gemini."""

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    # Query base (filtrable por sucursal)
    base = Factura.query
    if sucursal_id:
        base = base.filter(Factura.sucursal_id == sucursal_id)

    # --- Totales generales ---
    total_facturas = base.count()
    facturas_mes = base.filter(Factura.fecha >= inicio_mes).all()
    total_facturas_mes = len(facturas_mes)
    monto_mes = sum((f.total_factura or 0) for f in facturas_mes)

    validadas_mes = sum(1 for f in facturas_mes if f.estado == 'Validada')
    observadas_mes = sum(1 for f in facturas_mes if f.estado == 'Observada')

    # --- Sucursales y usuarios ---
    total_sucursales = Sucursal.query.filter_by(estado='Activa').count()
    total_usuarios = User.query.filter_by(estado='Activo').count()
    total_proveedores = Proveedor.query.filter_by(estado='Activo').count()

    # --- Desglose por sucursal (ultimo mes) ---
    sucursales_info = []
    for s in Sucursal.query.order_by(Sucursal.nombre).all():
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
        cat = Categoria.query.get(cid)
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

RESUMEN GENERAL:
- Total de facturas registradas: {total_facturas}
- Facturas del mes actual: {total_facturas_mes}
- Monto total del mes: ${monto_mes:.2f}
- Facturas validadas: {validadas_mes}
- Facturas observadas: {observadas_mes}
- Total de sucursales activas: {total_sucursales}
- Total de usuarios activos: {total_usuarios}
- Total de proveedores activos: {total_proveedores}

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
        modelo = _get_model()
        contexto = _recopilar_contexto(sucursal_id=sucursal_id)

        prompt = f"""Eres "Artesanos AI", el asistente inteligente del sistema "Artesanos Control" de ARTESANOS PIZZERIA (una empresa salvadorena con 3 sucursales: Usulutan, San Salvador y San Miguel).

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

CONTEXTO ACTUAL DE ARTESANOS CONTROL:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta_usuario}

RESPUESTA:"""

        respuesta = modelo.generate_content(prompt)
        return {
            'ok': True,
            'respuesta': respuesta.text
        }

    except ValueError as e:
        return {'ok': False, 'error': str(e)}
    except Exception as e:
        return {
            'ok': False,
            'error': f"Lo siento, tuve un problema al procesar tu consulta: {str(e)}"
        }

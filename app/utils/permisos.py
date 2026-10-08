"""
Decoradores de permisos para Artesanos Control.

Uso:
    @solo_owner              -> Solo owner
    @owner_o_supervisor      -> Owner + supervisor
    @puede_editar_factura    -> Owner + supervisor de la misma sucursal
"""
from functools import wraps
from flask import jsonify, abort, redirect, url_for, flash
from flask_login import current_user


# ============================================================
# DECORADORES PARA API (devuelven JSON)
# ============================================================
def solo_owner_api(f):
    """Solo el owner puede acceder. Devuelve JSON en caso de error."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_owner():
            return jsonify({
                'success': False,
                'error': 'Solo el administrador puede acceder a este recurso'
            }), 403
        return f(*args, **kwargs)
    return decorated


def owner_o_supervisor_api(f):
    """Owner o supervisor pueden acceder. Devuelve JSON en caso de error."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (current_user.is_owner() or current_user.is_supervisor()):
            return jsonify({
                'success': False,
                'error': 'Solo el administrador o supervisor pueden acceder'
            }), 403
        return f(*args, **kwargs)
    return decorated


# ============================================================
# DECORADORES PARA UI (redirigen o abortan)
# ============================================================
def solo_owner_ui(f):
    """Solo el owner puede acceder. Aborta con 403."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_owner():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def owner_o_supervisor_ui(f):
    """Owner o supervisor pueden acceder. Aborta con 403."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not (current_user.is_owner() or current_user.is_supervisor()):
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ============================================================
# HELPERS PARA FILTROS POR SUCURSAL
# ============================================================
def filtrar_sucursales_query(query, modelo_sucursal_id):
    """
    Aplica filtro por sucursal segun el rol del usuario.
    
    Uso:
        query = Factura.query
        query = filtrar_sucursales_query(query, Factura.sucursal_id)
    """
    if current_user.is_owner():
        return query  # Ve todas
    if current_user.sucursal_id:
        return query.filter(modelo_sucursal_id == current_user.sucursal_id)
    return query.filter(modelo_sucursal_id == -1)  # Sin sucursal = vacio


def puede_ver_recurso(sucursal_id):
    """Verifica si el usuario actual puede ver un recurso de esa sucursal."""
    if current_user.is_owner():
        return True
    return current_user.sucursal_id == sucursal_id


def puede_gestionar_recurso(sucursal_id):
    """Verifica si el usuario actual puede gestionar un recurso de esa sucursal."""
    if current_user.is_owner():
        return True
    if current_user.is_supervisor() and current_user.sucursal_id == sucursal_id:
        return True
    return False

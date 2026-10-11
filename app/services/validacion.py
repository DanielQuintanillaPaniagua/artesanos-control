import math


def _monto_valido(monto):
    """
    Valida que un monto sea un numero finito >= 0.
    Devuelve (ok, valor_o_error).
    """
    if monto is None:
        return True, 0.0
    try:
        v = float(monto)
    except (TypeError, ValueError):
        return False, 'no es un numero valido'
    if not math.isfinite(v):
        return False, 'no es un numero finito (NaN/Infinity)'
    if v < 0:
        return False, 'no puede ser negativo'
    return True, v


def validar_factura(detalles, total_factura, categorias_validas=None):
    """
    Valida que la suma de los detalles coincida con el total.

    Args:
        detalles: lista de dicts con 'monto' y opcionalmente 'categoria_id'
        total_factura: numero (float/int/str) con el total
        categorias_validas: set de IDs de categorias validas (opcional)

    Returns:
        tuple: (es_valida, mensaje, diferencia)
    """
    # Validar total
    try:
        total = float(total_factura)
    except (TypeError, ValueError):
        return False, "El total no es un numero valido", 0.0

    if not math.isfinite(total):
        return False, "El total no es un numero finito valido", 0.0

    if total < 0:
        return False, "El total no puede ser negativo", 0.0

    if not detalles:
        return False, "Debes ingresar al menos una categoria", total

    # Validar cada detalle y sumar
    suma = 0.0
    for i, d in enumerate(detalles):
        if not isinstance(d, dict):
            return False, f"Detalle {i+1}: formato invalido", total

        ok, valor = _monto_valido(d.get('monto', 0))
        if not ok:
            return False, f"Detalle {i+1}: el monto {valor}", total

        if valor > 0:
            suma += valor

        # Validar categoria_id si tenemos la lista
        if categorias_validas is not None:
            cat_id = d.get('categoria_id')
            if cat_id not in categorias_validas:
                return False, f"Detalle {i+1}: categoria invalida", total

    if suma == 0:
        return False, "Debes ingresar al menos un monto mayor a 0", total

    if not math.isfinite(suma):
        return False, "La suma de montos no es un numero finito", total

    diferencia = round(abs(suma - total), 2)

    if diferencia > 0.01:
        return (
            False,
            f"Error de cuadre: suma de categorias (${suma:.2f}) no coincide con el total (${total:.2f}). Diferencia: ${diferencia:.2f}",
            diferencia
        )

    return True, "Factura validada correctamente", 0.0
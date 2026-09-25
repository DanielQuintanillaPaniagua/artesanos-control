def validar_factura(detalles, total_factura):
    """
    Valida que la suma de los detalles coincida con el total.

    Returns:
        tuple: (es_valida, mensaje, diferencia)
    """
    if not detalles:
        return False, "Debes ingresar al menos una categoria", total_factura

    suma = sum(float(d.get('monto', 0)) for d in detalles if float(d.get('monto', 0)) > 0)

    if suma == 0:
        return False, "Debes ingresar al menos un monto mayor a 0", total_factura

    diferencia = round(abs(suma - total_factura), 2)

    if diferencia > 0.01:
        return (
            False,
            f"Error de cuadre: suma de categorias (${suma:.2f}) no coincide con el total (${total_factura:.2f}). Diferencia: ${diferencia:.2f}",
            diferencia
        )

    return True, "Factura validada correctamente", 0.0
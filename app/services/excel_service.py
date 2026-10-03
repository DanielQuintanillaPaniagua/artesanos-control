from io import BytesIO
from datetime import datetime, date
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


# ============================================================
# COLORES Y ESTILOS
# ============================================================
VERDE_OSCURO = "0F4630"
VERDE_CLARO = "E7F3EC"
GRIS_CLARO = "F4F6F5"
NARANJA = "C9963C"

BORDER_THIN = Border(
    left=Side(style='thin', color='D0D7D3'),
    right=Side(style='thin', color='D0D7D3'),
    top=Side(style='thin', color='D0D7D3'),
    bottom=Side(style='thin', color='D0D7D3'),
)


# ============================================================
# EXPORTAR FACTURAS A EXCEL (formato Artesanos)
# ============================================================
def exportar_facturas_excel(facturas, categorias):
    """Genera un Excel con formato profesional de Artesanos Pizzeria."""
    wb = Workbook()
    ws = wb.active
    ws.title = "FACTURAS"

    cats = sorted(categorias, key=lambda c: c.orden or 0)

    # Mapear grupos -> lista de columnas
    grupos = {}
    for idx, cat in enumerate(cats):
        col = 4 + idx
        grupo = (cat.grupo or 'OTROS').upper()
        grupos.setdefault(grupo, []).append(col)

    total_col = 4 + len(cats)

    # ============ FILA 1: ESTILOS BASE ============
    for col in range(1, total_col + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
        cell.font = Font(color="FFFFFF", bold=True, size=11)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = BORDER_THIN

    # ============ FILA 1: ESCRIBIR GRUPOS ANTES DE COMBINAR ============
    for grupo, cols in grupos.items():
        celda_principal = ws.cell(row=1, column=cols[0])
        celda_principal.value = grupo
        celda_principal.alignment = Alignment(horizontal='center', vertical='center')
        celda_principal.font = Font(color="FFFFFF", bold=True, size=11)

    # ============ FILA 1: COMBINAR DESPUES ============
    for grupo, cols in grupos.items():
        if len(cols) > 1:
            try:
                ws.merge_cells(start_row=1, start_column=cols[0], end_row=1, end_column=cols[-1])
            except Exception:
                pass

    # ============ FILA 2: TIPO DE DOCUMENTO ============
    for col in range(1, total_col + 1):
        cell = ws.cell(row=2, column=col)
        cell.fill = PatternFill(start_color=VERDE_CLARO, end_color=VERDE_CLARO, fill_type='solid')
        cell.font = Font(bold=True, size=10, color="0F4630")
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = BORDER_THIN

    # ============ FILA 3: NOMBRES DE CATEGORIAS ============
    for col in range(1, total_col + 1):
        cell = ws.cell(row=3, column=col)
        cell.fill = PatternFill(start_color=VERDE_CLARO, end_color=VERDE_CLARO, fill_type='solid')
        cell.font = Font(bold=True, size=10, color="0F4630")
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER_THIN

    ws.cell(row=3, column=1, value="FECHA")
    ws.cell(row=3, column=2, value="TIPO")
    ws.cell(row=3, column=3, value="DETALLE")

    for idx, cat in enumerate(cats):
        col = 4 + idx
        ws.cell(row=3, column=col, value=cat.nombre.upper())

    ws.cell(row=3, column=total_col, value="TOTAL")

    # ============ DATOS ============
    for row_idx, factura in enumerate(facturas, start=4):
        celda_fecha = ws.cell(row=row_idx, column=1)
        celda_fecha.value = factura.fecha
        celda_fecha.number_format = 'YYYY-MM-DD'
        celda_fecha.alignment = Alignment(horizontal='center', vertical='center')

        ws.cell(row=row_idx, column=2, value=factura.tipo_documento or '').alignment = Alignment(horizontal='center', vertical='center')

        proveedor_nombre = factura.proveedor.nombre if factura.proveedor else ''
        detalle_completo = proveedor_nombre
        if factura.detalle:
            detalle_completo += f" - {factura.detalle}"
        ws.cell(row=row_idx, column=3, value=detalle_completo)

        montos_por_cat = {d.categoria_id: d.monto for d in factura.detalles}
        total = 0
        for idx, cat in enumerate(cats):
            col = 4 + idx
            monto = montos_por_cat.get(cat.id, 0)
            if monto and monto > 0:
                cell = ws.cell(row=row_idx, column=col, value=float(monto))
                cell.number_format = '#,##0.00'
                total += float(monto)

        cell_total = ws.cell(row=row_idx, column=total_col, value=total or float(factura.total_factura or 0))
        cell_total.number_format = '#,##0.00'
        cell_total.font = Font(bold=True, size=10)

        for col in range(1, total_col + 1):
            ws.cell(row=row_idx, column=col).border = BORDER_THIN

    # ============ FILA DE TOTALES AL FINAL ============
    if facturas:
        fila_total = ws.max_row + 1

        # Celda con etiqueta
        celda_label = ws.cell(row=fila_total, column=1)
        celda_label.value = "TOTALES"
        celda_label.font = Font(bold=True, color="FFFFFF", size=11)
        celda_label.fill = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
        celda_label.alignment = Alignment(horizontal='center', vertical='center')

        # Celdas vacias con fondo verde en columnas B y C
        for col in [2, 3]:
            c = ws.cell(row=fila_total, column=col)
            c.fill = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')

        # Formulas SUM por cada categoria
        primera_fila_datos = 4
        ultima_fila_datos = fila_total - 1

        for idx, cat in enumerate(cats):
            col = 4 + idx
            col_letter = ws.cell(row=3, column=col).column_letter
            celda = ws.cell(row=fila_total, column=col)
            celda.value = f"=SUM({col_letter}{primera_fila_datos}:{col_letter}{ultima_fila_datos})"
            celda.font = Font(bold=True, size=10, color="0F4630")
            celda.fill = PatternFill(start_color=VERDE_CLARO, end_color=VERDE_CLARO, fill_type='solid')
            celda.number_format = '#,##0.00'
            celda.alignment = Alignment(horizontal='right', vertical='center')
            celda.border = BORDER_THIN

        # Formula TOTAL general
        col_total_letter = ws.cell(row=3, column=total_col).column_letter
        primera_col_letter = ws.cell(row=3, column=4).column_letter
        ultima_cat_letter = ws.cell(row=3, column=total_col - 1).column_letter
        celda_total = ws.cell(row=fila_total, column=total_col)
        celda_total.value = f"=SUM({primera_col_letter}{fila_total}:{ultima_cat_letter}{fila_total})"
        celda_total.font = Font(bold=True, size=11, color="FFFFFF")
        celda_total.fill = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
        celda_total.number_format = '#,##0.00'
        celda_total.alignment = Alignment(horizontal='right', vertical='center')
        celda_total.border = BORDER_THIN

        ws.row_dimensions[fila_total].height = 24

    # ============ ANCHO DE COLUMNAS ============
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 8
    ws.column_dimensions['C'].width = 35
    for idx in range(len(cats)):
        col_letter = ws.cell(row=3, column=4 + idx).column_letter
        ws.column_dimensions[col_letter].width = 11
    ws.column_dimensions[ws.cell(row=3, column=total_col).column_letter].width = 12

    # ============ FREEZE PANES ============
    ws.freeze_panes = 'D4'

    # Alturas
    ws.row_dimensions[1].height = 22
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 30

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def importar_facturas_excel(file_stream, categorias, sucursal_id, usuario_id):
    """Lee un Excel con el formato de Artesanos y devuelve lista de facturas.

    Devuelve: (ok, facturas_o_error, resumen)
    """
    from io import BytesIO

    # Convertir SpooledTemporaryFile a BytesIO (necesario para openpyxl)
    try:
        file_stream.seek(0)
        contenido = file_stream.read()
        buffer = BytesIO(contenido)
    except Exception as e:
        return False, f'Error leyendo archivo: {e}', {}

    # Cargar Excel
    try:
        wb = load_workbook(buffer, data_only=True)
        ws = wb.active
    except Exception as e:
        return False, f'Error abriendo Excel: {e}', {}

    # Detectar la fila de categorias (buscamos en las primeras 10 filas)
    header_row = None
    for r in range(1, 10):
        row_values = [ws.cell(row=r, column=c).value for c in range(4, 30)]
        # Si mas de 3 celdas no son None, es probable que sea la fila de headers
        if sum(1 for v in row_values if v) >= 3:
            header_row = r
            break

    if not header_row:
        return False, 'No se encontro la fila de encabezados (categorias)', {}

    # Mapear columnas: {col_index: categoria_id}
    mapa_columnas = {}
    nombres_cats = {c.nombre.upper(): c.id for c in categorias}

    for col in range(4, 30):
        val = ws.cell(row=header_row, column=col).value
        if val:
            nombre = str(val).strip().upper()
            if nombre in nombres_cats:
                mapa_columnas[col] = nombres_cats[nombre]
            elif nombre == 'TOTAL':
                break

    if not mapa_columnas:
        return False, 'No se encontraron categorias validas en el Excel. Verifica que la fila de encabezados tenga los nombres de categorias.', {}

    # Leer datos
    facturas_data = []
    resumen = {
        'total_filas': 0,
        'validas': 0,
        'sin_fecha': 0,
        'sin_monto': 0,
    }

    for r in range(header_row + 1, ws.max_row + 1):
        fecha_val = ws.cell(row=r, column=1).value
        tipo_doc = ws.cell(row=r, column=2).value
        detalle = ws.cell(row=r, column=3).value

        # Saltear filas sin fecha Y sin detalle
        if not fecha_val and not detalle:
            continue

        # Saltear filas sin fecha valida
        if not fecha_val:
            resumen['sin_fecha'] += 1
            continue

        # Convertir fecha
        if isinstance(fecha_val, datetime):
            fecha = fecha_val.date()
        elif isinstance(fecha_val, date):
            fecha = fecha_val
        elif isinstance(fecha_val, str):
            try:
                fecha = datetime.strptime(fecha_val[:10], '%Y-%m-%d').date()
            except ValueError:
                resumen['sin_fecha'] += 1
                continue
        else:
            resumen['sin_fecha'] += 1
            continue

        # Leer montos por categoria
        detalles = []
        total = 0
        for col, cat_id in mapa_columnas.items():
            monto = ws.cell(row=r, column=col).value
            if monto and isinstance(monto, (int, float)) and monto > 0:
                detalles.append({
                    'categoria_id': cat_id,
                    'monto': float(monto),
                })
                total += float(monto)

        if not detalles or total == 0:
            resumen['sin_monto'] += 1
            continue

        resumen['total_filas'] += 1
        resumen['validas'] += 1

        facturas_data.append({
            'fecha': fecha,
            'tipo_documento': (str(tipo_doc).strip() if tipo_doc else '')[:30],
            'detalle': (str(detalle).strip() if detalle else '')[:200],
            'total': total,
            'detalles': detalles,
        })

    return True, facturas_data, resumen

# ============================================================
# EXPORTAR USUARIOS A EXCEL
# ============================================================
def exportar_usuarios_excel(usuarios):
    """Exporta la lista de usuarios a Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "USUARIOS"

    headers = ['ID', 'Nombre', 'Usuario', 'Email', 'Rol', 'Sucursal', 'Estado']
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
        cell.border = BORDER_THIN

    for row_idx, u in enumerate(usuarios, start=2):
        ws.cell(row=row_idx, column=1, value=u.id)
        ws.cell(row=row_idx, column=2, value=u.nombre or '')
        ws.cell(row=row_idx, column=3, value=u.usuario or '')
        ws.cell(row=row_idx, column=4, value=u.email or '')
        ws.cell(row=row_idx, column=5, value=u.rol or '')
        ws.cell(row=row_idx, column=6, value=u.sucursal.nombre if u.sucursal else 'Todas')
        ws.cell(row=row_idx, column=7, value=u.estado or '')

        for col in range(1, 8):
            ws.cell(row=row_idx, column=col).border = BORDER_THIN

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 30
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 18
    ws.column_dimensions['G'].width = 10

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ============================================================
# EXPORTAR SUCURSALES A EXCEL
# ============================================================
def exportar_sucursales_excel(sucursales_data):
    """Exporta la lista de sucursales a Excel."""
    wb = Workbook()
    ws = wb.active
    ws.title = "SUCURSALES"

    headers = ['ID', 'Nombre', 'Direccion', 'Telefono', 'Estado', 'Usuarios', 'Facturas (mes)']
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
        cell.alignment = Alignment(horizontal='center')
        cell.border = BORDER_THIN

    for row_idx, item in enumerate(sucursales_data, start=2):
        s = item['obj']
        ws.cell(row=row_idx, column=1, value=s.id)
        ws.cell(row=row_idx, column=2, value=s.nombre or '')
        ws.cell(row=row_idx, column=3, value=s.direccion or '')
        ws.cell(row=row_idx, column=4, value=s.telefono or '')
        ws.cell(row=row_idx, column=5, value=s.estado or '')
        ws.cell(row=row_idx, column=6, value=item.get('usuarios', 0))
        ws.cell(row=row_idx, column=7, value=item.get('facturas_mes', 0))

        for col in range(1, 8):
            ws.cell(row=row_idx, column=col).border = BORDER_THIN

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 10
    ws.column_dimensions['G'].width = 15

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

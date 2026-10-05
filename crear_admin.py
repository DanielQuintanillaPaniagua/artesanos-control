# crear_admin.py
# Script de inicializacion de ARTESANOS CONTROL
# Crea unicamente:
#   - 1 sucursal base
#   - 1 usuario owner
#   - 21 categorias del Excel (necesarias para el sistema)

from app import create_app, db
from app.models.user import User
from app.models.sucursal import Sucursal
from app.models.categoria import Categoria

app = create_app()

with app.app_context():
    print("=" * 60)
    print("INICIALIZANDO ARTESANOS CONTROL")
    print("=" * 60)

    # ===== 1. SUCURSAL BASE =====
    print("\n[1/3] Creando sucursal base...")
    sucursal = Sucursal.query.filter_by(nombre="Owner").first()
    if not sucursal:
        sucursal = Sucursal(
            nombre="Owner",
            direccion="Sucursal principal",
            telefono=None,
            estado="Activa",
        )
        db.session.add(sucursal)
        db.session.commit()
        print("  + Sucursal creada: Owner")
    else:
        print("  = Sucursal ya existe: Owner")

    # ===== 2. CATEGORIAS (las 21 del Excel) =====
    print("\n[2/3] Creando categorias...")
    categorias_data = [
        {"nombre": "Comida", "grupo": "Abastecimiento", "orden": 1},
        {"nombre": "Bebida", "grupo": "Abastecimiento", "orden": 2},
        {"nombre": "Limpieza", "grupo": "Abastecimiento", "orden": 3},
        {"nombre": "Empaques", "grupo": "Materiales", "orden": 4},
        {"nombre": "Equipo", "grupo": "Materiales", "orden": 5},
        {"nombre": "Alquiler", "grupo": "Materiales", "orden": 6},
        {"nombre": "Cable", "grupo": "Materiales", "orden": 7},
        {"nombre": "EEO", "grupo": "Materiales", "orden": 8},
        {"nombre": "Inversion", "grupo": "Mantenimiento", "orden": 9},
        {"nombre": "Mantenimiento", "grupo": "Mantenimiento", "orden": 10},
        {"nombre": "Combustible", "grupo": "Mantenimiento", "orden": 11},
        {"nombre": "Comida Personal", "grupo": "Personal", "orden": 12},
        {"nombre": "Publicidad", "grupo": "Marketing", "orden": 13},
        {"nombre": "Gastos Personales", "grupo": "Personal", "orden": 14},
        {"nombre": "Otros", "grupo": "Varios", "orden": 15},
        {"nombre": "Papeleria", "grupo": "Varios", "orden": 16},
        {"nombre": "Unigas", "grupo": "Servicios", "orden": 17},
        {"nombre": "Planilla", "grupo": "Personal", "orden": 18},
        {"nombre": "Descuentos en Planilla", "grupo": "Personal", "orden": 19},
        {"nombre": "Servicios Profesionales", "grupo": "Servicios", "orden": 20},
        {"nombre": "Impuestos ISSS", "grupo": "Impuestos", "orden": 21},
    ]
    nuevas = 0
    for c in categorias_data:
        if not Categoria.query.filter_by(nombre=c["nombre"]).first():
            db.session.add(Categoria(**c, estado="Activa"))
            nuevas += 1
    db.session.commit()
    print(f"  + {nuevas} categorias nuevas (total: {Categoria.query.count()})")

    # ===== 3. USUARIO OWNER =====
    print("\n[3/3] Creando usuario owner...")
    if not User.query.filter_by(usuario="owner").first():
        owner = User(
            nombre="Owner",
            usuario="owner",
            email=None,
            rol="owner",
            sucursal_id=None,  # Los owners no tienen sucursal
        )
        owner.set_password("artesanos2026")
        db.session.add(owner)
        db.session.commit()
        print("  + Owner creado: owner / artesanos2026")
    else:
        print("  = Owner ya existe: owner")

    # ===== RESUMEN =====
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  Sucursales:  {Sucursal.query.count()}")
    print(f"  Categorias:  {Categoria.query.count()}")
    print(f"  Usuarios:    {User.query.count()}")
    print("=" * 60)
    print("\nCREDENCIALES:")
    print("  Usuario:    owner")
    print("  Contrasena: artesanos2026")
    print("\nIMPORTANTE: cambia la contrasena despues del primer login.")
    print("=" * 60)

# crear_admin.py
# Script para crear datos iniciales de ARTESANOS CONTROL
# - 2 sucursales
# - 1 usuario owner (dueño)
# - 1 usuario empleado (por sucursal)
# - 21 categorias del Excel
# - 8 proveedores de prueba

from app import create_app, db
from app.models.user import User
from app.models.sucursal import Sucursal
from app.models.proveedor import Proveedor
from app.models.categoria import Categoria

app = create_app()

with app.app_context():
    print("=" * 60)
    print("CREANDO DATOS INICIALES DE ARTESANOS CONTROL")
    print("=" * 60)

    # ===== 1. SUCURSALES =====
    print("\n[1/5] Creando sucursales...")
    sucursales_data = [
        {"nombre": "Usulutan", "direccion": "Calle Principal #123, Usulutan", "telefono": "+503 2600 1111"},
        {"nombre": "San Salvador", "direccion": "Av. Independencia #456, San Salvador", "telefono": "+503 2200 2222"},
        {"nombre": "San Miguel", "direccion": "Blvd. Central #789, San Miguel", "telefono": "+503 2600 3333"},
    ]
    sucursales = []
    for s in sucursales_data:
        if not Sucursal.query.filter_by(nombre=s["nombre"]).first():
            suc = Sucursal(**s, estado="Activa")
            db.session.add(suc)
            sucursales.append(suc)
            print(f"  + Sucursal: {s['nombre']}")
        else:
            print(f"  = Sucursal ya existe: {s['nombre']}")
    db.session.commit()

    # Recargar para obtener IDs
    suc_usulutan = Sucursal.query.filter_by(nombre="Usulutan").first()
    suc_san_salvador = Sucursal.query.filter_by(nombre="San Salvador").first()
    suc_san_miguel = Sucursal.query.filter_by(nombre="San Miguel").first()

    # ===== 2. CATEGORIAS (las 21 del Excel) =====
    print("\n[2/5] Creando categorias...")
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
    for c in categorias_data:
        if not Categoria.query.filter_by(nombre=c["nombre"]).first():
            db.session.add(Categoria(**c, estado="Activa"))
    db.session.commit()
    print(f"  + {Categoria.query.count()} categorias creadas")

    # ===== 3. PROVEEDORES =====
    print("\n[3/5] Creando proveedores...")
    proveedores_data = [
        {"nombre": "Comercial El Sol", "telefono": "+503 2222 1111", "email": "ventas@elsol.com"},
        {"nombre": "Insumos del Campo", "telefono": "+503 2222 2222", "email": "contacto@insumos.com"},
        {"nombre": "Productos Artesanales S.A.", "telefono": "+503 2222 3333", "email": "info@artesanales.com"},
        {"nombre": "Distribuidora La Central", "telefono": "+503 2222 4444", "email": "ventas@lacentral.com"},
        {"nombre": "Pollos del Valle", "telefono": "+503 2222 5555", "email": "pedidos@pollosvalle.com"},
        {"nombre": "Lacteos San Jose", "telefono": "+503 2222 6666", "email": "info@lacteossj.com"},
        {"nombre": "Bebidas del Pacifico", "telefono": "+503 2222 7777", "email": "ventas@bepacifico.com"},
        {"nombre": "Limpieza Total", "telefono": "+503 2222 8888", "email": "contacto@limpiezatotal.com"},
    ]
    for p in proveedores_data:
        if not Proveedor.query.filter_by(nombre=p["nombre"]).first():
            db.session.add(Proveedor(**p, estado="Activo"))
    db.session.commit()
    print(f"  + {Proveedor.query.count()} proveedores creados")

    # ===== 4. USUARIOS =====
    print("\n[4/5] Creando usuarios...")

    # Owner
    if not User.query.filter_by(usuario="admin").first():
        admin = User(
            nombre="Administrador General",
            usuario="admin",
            email="admin@artesanos.com",
            rol="owner",
            sucursal_id=suc_san_salvador.id if suc_san_salvador else None
        )
        admin.set_password("admin123")
        db.session.add(admin)
        print("  + Owner creado: admin / admin123")

    # Empleado Usulutan
    if not User.query.filter_by(usuario="empleado").first():
        emp = User(
            nombre="Juan Perez",
            usuario="empleado",
            email="empleado@artesanos.com",
            rol="empleado",
            sucursal_id=suc_usulutan.id if suc_usulutan else None
        )
        emp.set_password("empleado123")
        db.session.add(emp)
        print("  + Empleado creado: empleado / empleado123 (Usulutan)")

    # Empleado San Salvador
    if not User.query.filter_by(usuario="empleado2").first():
        emp2 = User(
            nombre="Maria Lopez",
            usuario="empleado2",
            email="empleado2@artesanos.com",
            rol="empleado",
            sucursal_id=suc_san_salvador.id if suc_san_salvador else None
        )
        emp2.set_password("empleado123")
        db.session.add(emp2)
        print("  + Empleado creado: empleado2 / empleado123 (San Salvador)")

    db.session.commit()

    # ===== 5. RESUMEN =====
    print("\n[5/5] Resumen final:")
    print("=" * 60)
    print(f"  Sucursales: {Sucursal.query.count()}")
    print(f"  Categorias: {Categoria.query.count()}")
    print(f"  Proveedores: {Proveedor.query.count()}")
    print(f"  Usuarios:   {User.query.count()}")
    print("=" * 60)
    print("\nCREDENCIALES DE PRUEBA:")
    print("  OWNER:")
    print("    Usuario:    admin")
    print("    Contrasena: admin123")
    print("  EMPLEADO (Usulutan):")
    print("    Usuario:    empleado")
    print("    Contrasena: empleado123")
    print("  EMPLEADO (San Salvador):")
    print("    Usuario:    empleado2")
    print("    Contrasena: empleado123")
    print("=" * 60)

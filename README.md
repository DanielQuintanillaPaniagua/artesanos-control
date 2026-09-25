# ARTESANOS CONTROL

Sistema web de control y validacion de facturas para ARTESANOS PIZZERIA.

## Descripcion

Aplicacion Flask que permite a los empleados de cada sucursal registrar facturas
de compra, con un desglose obligatorio por categorias (Comida, Bebida, Limpieza,
etc.). El sistema valida que la suma de categorias coincida con el total de la
factura antes de guardarla, evitando errores de cuadre.

## Caracteristicas

- Autenticacion con roles (Owner / Empleado)
- Registro de facturas con validacion automatica de cuadre
- 21 categorias de gasto (segun Excel de la empresa)
- Multi-sucursal (Usulutan, San Salvador, San Miguel)
- Dashboard con metricas por sucursal
- Tema visual con la paleta de la marca (verde + rojo + blanco)

## Tecnologias

- **Backend:** Python 3.9 + Flask
- **Base de datos:** MySQL (XAMPP local) + SQLAlchemy
- **Frontend:** HTML5 + CSS3 + JavaScript + Bootstrap 5
- **Autenticacion:** Flask-Login con hashing scrypt
- **IA:** Google Gemini API (fase futura)



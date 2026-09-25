# run.py
from app import create_app, db
import os

app = create_app()

# Parche temporal de emergencia
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = 'clave-temporal-de-emergencia-12345'
    print("⚠️  Usando SECRET_KEY temporal (arregla el .env)")

with app.app_context():
    db.create_all()
    print("Base de datos inicializada en instance/artesanos.db")


if __name__ == '__main__':
    app.run(debug=True, port=5000)

# run.py
import os
from app import create_app, db

app = create_app()

# Verificar que SECRET_KEY este configurada
if not app.config.get('SECRET_KEY'):
    raise RuntimeError(
        "FLASK_SECRET_KEY no configurada en el .env. "
        "Copia .env.example a .env y configura la variable."
    )

with app.app_context():
    db.create_all()
    print("Base de datos inicializada")


if __name__ == '__main__':
    # Debug solo si FLASK_DEBUG=True (por defecto: False)
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    app.run(debug=debug_mode, port=port)

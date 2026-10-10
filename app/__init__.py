import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesion para continuar'
    login_manager.login_message_category = 'warning'

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import bp as auth_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.facturas import bp as facturas_bp
    from app.routes.facturas_ui import bp as facturas_ui_bp
    from app.routes.editar_factura import editar_factura_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.perfil import bp as perfil_bp
    from app.routes.artesanos_ai import bp as artesanos_ai_bp
    from app.routes.ai_api import bp as ai_api_bp
    from app.routes.recuperar import bp as recuperar_bp
    from app.routes.dashboard_api import bp as dashboard_api_bp
    from app.routes.usuarios_api import bp as usuarios_api_bp
    from app.routes.sucursales_api import bp as sucursales_api_bp
    from app.routes.proveedores_api import bp as proveedores_api_bp
    from app.routes.categorias_api import bp as categorias_api_bp
    from app.routes.reportes_api import bp as reportes_api_bp
    from app.routes.chat_api import bp as chat_api_bp
    from app.routes.chat_ui import bp as chat_ui_bp
    


    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(facturas_bp)
    
    app.register_blueprint(facturas_ui_bp)
    app.register_blueprint(editar_factura_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(artesanos_ai_bp)
    app.register_blueprint(ai_api_bp)
    app.register_blueprint(recuperar_bp)
    app.register_blueprint(dashboard_api_bp)
    app.register_blueprint(usuarios_api_bp)
    app.register_blueprint(sucursales_api_bp)
    app.register_blueprint(proveedores_api_bp)
    app.register_blueprint(categorias_api_bp)
    app.register_blueprint(reportes_api_bp)
    app.register_blueprint(chat_api_bp)
    app.register_blueprint(chat_ui_bp)


    return app
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

# Rate limiter global (para proteger el login, etc.)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from flask_login import current_user

    def _key_func_usuario():
        """Rate limit por usuario logueado, o por IP si no hay sesion."""
        try:
            if current_user and current_user.is_authenticated:
                return f"user:{current_user.id}"
        except Exception:
            pass
        return get_remote_address()

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[],  # sin limite global; lo aplicamos endpoint por endpoint
    )
except ImportError:
    limiter = None
    _key_func_usuario = None


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Limite de tamaño de archivos subidos: 5 MB.
    # Evita que alguien suba un Excel gigante y tumbe el servidor.
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

    # ============================================================
    # SEGURIDAD: Host header / Proxy
    # ============================================================
    # En produccion forzamos SERVER_NAME para que url_for(_external=True)
    # ignore el header Host (evita Host poisoning en recuperar contrasena).
    # En desarrollo (FLASK_ENV=development) no lo forzamos.
    entorno = os.getenv('FLASK_ENV', 'production')
    if entorno == 'development':
        app.config['SERVER_NAME'] = None  # No forzar, usar Host header en local
        app.config['PREFERRED_URL_SCHEME'] = 'http'
    else:
        app.config['SERVER_NAME'] = os.getenv('SERVER_NAME', 'artesanos-control.duckdns.org')
        app.config['PREFERRED_URL_SCHEME'] = 'https'

    # ProxyFix: confia en los headers X-Forwarded-* de Nginx (1 nivel).
    # Necesario para que Flask sepa que esta detras de HTTPS.
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=0,
    )

    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Rate limiter
    if limiter is not None:
        limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesion para continuar'
    login_manager.login_message_category = 'warning'

    # ============================================================
    # SEGURIDAD: Cookies y headers HTTP
    # ============================================================
    es_dev = (entorno == 'development')

    app.config['SESSION_COOKIE_HTTPONLY'] = True          # JS no puede leer la cookie
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'         # protege contra CSRF cross-site
    app.config['SESSION_COOKIE_SECURE'] = not es_dev      # solo HTTPS en prod
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_SECURE'] = not es_dev
    app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 8  # 8 horas

    @app.after_request
    def _headers_seguridad(response):
        # Evita clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Evita que el navegador adivine el tipo MIME
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Referrer: no filtrar URL completa a terceros
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # HSTS: solo en produccion con HTTPS
        if not es_dev:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Content-Security-Policy:
        # - 'self': solo recursos del propio dominio
        # - 'unsafe-inline' en style: necesario por los estilos inline de los templates
        # - 'unsafe-inline' en script: por los onclick de los templates. Deuda tecnica: migrar a event listeners.
        # - cdn.jsdelivr.net: Bootstrap CSS/JS
        # - fonts.googleapis.com / fonts.gstatic.com: Google Fonts
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none';"
        )
        return response

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        """
        Carga al usuario desde la cookie de sesion.

        Reglas:
        - Si el usuario no existe -> None (cerrar sesion)
        - Si el usuario esta Inactivo -> None (cerrar sesion)
        - Si su sucursal esta Inactiva -> None (cerrar sesion)
        - Si todo OK -> el User
        """
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None

        u = db.session.get(User, uid)
        if not u:
            return None

        if u.estado != 'Activo':
            return None

        # Owner siempre puede entrar (no validamos su sucursal)
        if not u.is_owner() and u.sucursal and u.sucursal.estado != 'Activa':
            return None

        return u

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
"""Inicialização da aplicação Flask SRA."""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.utils.logger import setup_sra_logging

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'


def create_app(config_class=Config):
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Configurar logging personalizado
    setup_sra_logging(app)

    from app.routes.auth import auth_bp
    from app.routes.principal import principal_bp
    from app.routes.admin import admin_bp
    from app.routes.relatorio import relatorio_bp
    from app.routes.configuracoes import configuracoes_bp
    from app.routes.api import api_bp
    from app.routes.acoes_relatorio import acoes_bp
    from app.routes.capitulos import capitulos_bp
    from app.models.usuario import Usuario

    app.register_blueprint(auth_bp)
    app.register_blueprint(principal_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(relatorio_bp)
    app.register_blueprint(configuracoes_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(acoes_bp)
    app.register_blueprint(capitulos_bp)

    @login_manager.user_loader
    def load_user(user_id):
        """Carrega usuário pelo ID para Flask-Login."""
        return Usuario.query.get(int(user_id))

    @app.after_request
    def _configure_security_headers(response):
        """Adiciona headers de segurança e CORS para recursos externos."""
        # Permite que scripts de terceiros (CDN) funcionem sem Tracking Prevention
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        response.headers['Cross-Origin-Embedder-Policy'] = 'credentialless'
        
        # Headers adicionais para desabilitar Tracking Prevention no Firefox/Safari
        response.headers['Permissions-Policy'] = 'storage-access=*'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response

    @app.context_processor
    def _inject_static_versioning():
        """Expõe `static_v(path)` para gerar cache-busting baseado no
        mtime do arquivo estático. Uso no template:
        `?v={{ static_v('js/docx-editor-bundle.js') }}`"""
        from flask_wtf.csrf import generate_csrf
        
        static_dir = os.path.join(app.root_path, 'static')

        def static_v(rel_path):
            try:
                return str(int(os.path.getmtime(
                    os.path.join(static_dir, rel_path)
                )))
            except OSError:
                return '0'

        return {
            'static_v': static_v,
            'csrf_token': generate_csrf
        }

    return app

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
setattr(login_manager, "login_view", "auth.login")


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
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"

        # Headers adicionais para desabilitar Tracking Prevention no Firefox/Safari
        response.headers["Permissions-Policy"] = "storage-access=*"
        response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

    @app.context_processor
    def _inject_static_versioning():
        """Expõe `static_v(path)` para gerar cache-busting baseado no
        mtime do arquivo estático. Uso no template:
        `?v={{ static_v('js/docx-editor-bundle.js') }}`"""
        from flask_wtf.csrf import generate_csrf

        static_dir = os.path.join(app.root_path, "static")

        def static_v(rel_path):
            try:
                return str(int(os.path.getmtime(os.path.join(static_dir, rel_path))))
            except OSError:
                return "0"

        return {"static_v": static_v, "csrf_token": generate_csrf}

    # ============================================================
    # Handlers de erro com logging
    # ============================================================

    @app.errorhandler(400)
    def bad_request(error):
        """Handler para erros 400 Bad Request."""
        from flask import render_template

        app.logger.error("400 Bad Request: %s", error)
        return render_template("error_400.html", message=str(error)), 400

    @app.errorhandler(403)
    def forbidden(error):
        """Handler para erros 403 Forbidden."""
        app.logger.error("403 Forbidden: %s", error)
        return {"error": "Forbidden", "message": str(error), "status": 403}, 403

    @app.errorhandler(404)
    def not_found(error):
        """Handler para erros 404 Not Found."""
        app.logger.error("404 Not Found: %s", error)
        return {"error": "Not Found", "message": str(error), "status": 404}, 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handler para erros 500 Internal Server Error."""
        app.logger.error("500 Internal Server Error: %s", error)
        db.session.rollback()
        return {
            "error": "Internal Server Error",
            "message": "Ocorreu um erro no servidor. Por favor, tente novamente.",
            "status": 500,
        }, 500

    return app

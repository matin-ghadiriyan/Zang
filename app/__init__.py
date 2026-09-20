import os
from flask import Flask, render_template
from flask_migrate import upgrade, stamp
from app.extensions import db, migrate
from app.request_limiter import rate_limit
from app.routes import Blue_prints
from config import Config

def create_app() -> Flask:
    """Create and configure the application."""

    # --- create the application ---------------------------------------------
    app = Flask(
        __name__,
        template_folder="templats",
        static_folder="static"
    )

    # --- load configuration -------------------------------------------------
    app.config.from_object(Config)

    # --- ensure required configuration exists -------------------------------
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = Config.SECRET_KEY

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///zang.db"

    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    # --- configure database -------------------------------------------------
    db.init_app(app)

    # --- configure migration ------------------------------------------------
    migrate.init_app(app, db)

    # --- Blueprints ----------------------------------------------------------
    for blue_print in Blue_prints():
        app.register_blueprint(blue_print)

    # --- Error handlers ------------------------------------------------------
    '''404 - Not Found'''
    @app.errorhandler(404)
    def not_found(_):
        return render_template("errors/404.html"), 404

    '''500 - Internal Server Error'''
    @app.errorhandler(500)
    def internal_server_error(_):
        return render_template("errors/500.html"), 500

    '''403 - Forbidden'''
    @app.errorhandler(403)
    def forbidden(_):
        return render_template("errors/403.html"), 403

    '''401 - Unauthorized'''
    @app.errorhandler(401)
    def unauthorized(_):
        return render_template("errors/401.html"), 401

    # --- context processor --------------------------------------------------
    @app.context_processor
    def inject_user():
        """Inject current user into templates."""
        from app.Access import current_user
        return {"current_user": current_user()}

    # --- rate limiter --------------------------------------------------------
    @app.before_request
    def before_request():
        """Check if the request is rate limited."""
        if not rate_limit():
            return render_template("errors/429.html"), 429

    # --- upgrade database ----------------------------------------------------
    with app.app_context():
        _auto_update_database(app)

    return app


def _auto_update_database(app: Flask) -> None:
    """Run migrations or create database tables."""

    migrations_dir = os.path.join(app.root_path, "..", "migrations")

    if os.path.isdir(migrations_dir):
        try:
            upgrade()
            return
        except Exception:
            db.session.rollback()

            try:
                stamp()
                upgrade()
                return
            except Exception:
                pass

    db.create_all()

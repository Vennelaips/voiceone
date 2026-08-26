import os
from datetime import datetime
from flask import Flask, render_template, session
from config import Config
from database import get_db
from routes.auth_routes import auth_bp
from routes.poll_routes import poll_bp
from routes.forum_routes import forum_bp
from routes.api_routes import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(poll_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(api_bp)

    # Global Template Context
    @app.context_processor
    def inject_global_context():
        return {
            "is_authenticated": session.get("is_authenticated", False),
            "citizen_name": session.get("citizen_name", ""),
            "citizen_age": session.get("citizen_age", ""),
            "citizen_hash": session.get("citizen_hash", ""),
            "current_year": datetime.now().year
        }

    # Custom Jinja filters
    @app.template_filter("time_ago")
    def time_ago(iso_str):
        if not iso_str:
            return "recently"
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", ""))
            diff = datetime.now() - dt
            seconds = diff.total_seconds()
            if seconds < 60:
                return "just now"
            if seconds < 3600:
                return f"{int(seconds // 60)}m ago"
            if seconds < 86400:
                return f"{int(seconds // 3600)}h ago"
            return f"{int(seconds // 86400)}d ago"
        except Exception:
            return "recently"

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("500.html"), 500

    return app

app = create_app()

if __name__ == "__main__":
    # Pre-initialize DB
    get_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)

import os
from flask import Flask, render_template, session, redirect, url_for

from db import DB_PATH, init_db
from routes.auth import bp as auth_bp
from routes.admin import bp as admin_bp
from routes.teacher import bp as teacher_bp
from routes.student import bp as student_bp
from routes.charts import bp as charts_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SMARTCONNECT_SECRET", "dev-secret-change-me")

    # Auto-create the DB the first time the app boots (schema only, no seed data).
    if not os.path.exists(DB_PATH):
        init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(charts_bp)

    @app.context_processor
    def inject_globals():
        return {"current_role": session.get("role"), "current_name": session.get("full_name")}

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors.html", code=403,
                                message="You don't have permission to view that page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors.html", code=404,
                                message="That page doesn't exist."), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

"""Register all UITOP blueprints."""


def register_blueprints(app):
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.computers import bp as computers_bp
    from routes.servers import bp as servers_bp
    from routes.assets import bp as assets_bp
    from routes.backup import bp as backup_bp
    from routes.restore import bp as restore_bp
    from routes.monitoring import bp as monitoring_bp
    from routes.reports import bp as reports_bp
    from routes.analytics import bp as analytics_bp
    from routes.users import bp as users_bp
    from routes.settings import bp as settings_bp
    from routes.ai import bp as ai_bp
    from routes.helpdesk import bp as helpdesk_bp
    from routes.software import bp as software_bp
    from routes.licenses import bp as licenses_bp
    from routes.vendors import bp as vendors_bp
    from routes.files import bp as files_bp
    from routes.network import bp as network_bp
    from routes.printers import bp as printers_bp
    from routes.modules import bp as modules_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(computers_bp)
    app.register_blueprint(servers_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(printers_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(software_bp)
    app.register_blueprint(licenses_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(restore_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(helpdesk_bp)
    app.register_blueprint(modules_bp)

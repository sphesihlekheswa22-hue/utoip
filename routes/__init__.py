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
    from routes.documents import bp as documents_bp
    from routes.workspace import bp as workspace_bp
    from routes.workflows import bp as workflows_bp
    from routes.workflows import tasks_bp
    from routes.catalog import bp as catalog_bp
    from routes.network import bp as network_bp
    from routes.printers import bp as printers_bp
    from routes.maintenance import bp as maintenance_bp
    from routes.security import bp as security_bp
    from routes.calendar import bp as calendar_bp
    from routes.analysis import bp as analysis_bp
    from routes.audit import bp as audit_bp
    from routes.modules import bp as modules_bp
    from routes.discovery import bp as discovery_bp
    from routes.profile import bp as profile_bp
    from routes.notifications import bp as notifications_bp
    from routes.employee import bp as employee_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(discovery_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(employee_bp)
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
    app.register_blueprint(documents_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(workflows_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(restore_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(helpdesk_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(modules_bp)

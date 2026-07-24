"""Generic module page renderer for scaffolded templates."""
from flask import Blueprint, abort, render_template

bp = Blueprint("modules", __name__)

ALLOWED = {
    "alerts": ["index", "details", "history"],
    "knowledge": ["index", "create", "details", "edit"],
    "maintenance": ["index", "create", "details", "edit", "history"],
    "documents": ["index", "create", "details", "edit"],
    "roles": ["index", "create", "edit", "details"],
    "departments": ["index", "create", "edit", "details"],
    "notifications": ["index"],
    "profile": ["index", "edit"],
    "audit": ["index", "details"],
    "calendar": ["index", "create", "details"],
    "security": ["index", "create", "details"],
    "search": ["index"],
}


def render_module(module, page_name):
    pages = ALLOWED.get(module)
    if not pages or page_name not in pages:
        abort(404)
    return render_template(f"{module}/{page_name}.html", active=module)


@bp.get("/m/<module>/<page>")
def page(module, page):
    return render_module(module, page)


def _register_module_routes(module_name):
    def index_view():
        return render_module(module_name, "index")

    index_view.__name__ = f"{module_name}_index"
    bp.add_url_rule(f"/{module_name}/", view_func=index_view)

    def sub_view(page_name):
        return render_module(module_name, page_name)

    sub_view.__name__ = f"{module_name}_page"
    bp.add_url_rule(f"/{module_name}/<page_name>", view_func=sub_view)


for _mod in ALLOWED:
    _register_module_routes(_mod)

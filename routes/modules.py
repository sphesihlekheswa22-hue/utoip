"""Generic module page renderer for scaffolded templates."""
from flask import Blueprint, abort, redirect, render_template, url_for

bp = Blueprint("modules", __name__)

ALLOWED = {
    "alerts": ["index", "details", "history"],
    "knowledge": ["index", "create", "details", "edit"],
    "roles": ["index", "create", "edit", "details"],
    "departments": ["index", "create", "edit", "details"],
    "search": ["index"],
}

# Fold scaffold Roles / Departments into the Users identity hub
IDENTITY_REDIRECTS = {
    "roles": "roles",
    "departments": "departments",
}


def render_module(module, page_name):
    if module in IDENTITY_REDIRECTS:
        return redirect(url_for("users.index", view=IDENTITY_REDIRECTS[module]))
    pages = ALLOWED.get(module)
    if not pages or page_name not in pages:
        abort(404)
    return render_template(f"{module}/{page_name}.html", active=module)


@bp.get("/m/<module>/<page>")
def page(module, page):
    return render_module(module, page)


def _register_module_routes(module_name):
    def index_view():
        if module_name in IDENTITY_REDIRECTS:
            return redirect(url_for("users.index", view=IDENTITY_REDIRECTS[module_name]))
        return render_module(module_name, "index")

    index_view.__name__ = f"{module_name}_index"
    bp.add_url_rule(f"/{module_name}/", view_func=index_view)

    def sub_view(page_name):
        if module_name in IDENTITY_REDIRECTS:
            return redirect(url_for("users.index", view=IDENTITY_REDIRECTS[module_name]))
        return render_module(module_name, page_name)

    sub_view.__name__ = f"{module_name}_page"
    bp.add_url_rule(f"/{module_name}/<page_name>", view_func=sub_view)


for _mod in ALLOWED:
    _register_module_routes(_mod)

"""Reports — official reporting center (generate, schedule, export, share)."""
from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from uitop.services import reports_view as rv
from uitop.utils.pagination import paginate

bp = Blueprint("reports", __name__, url_prefix="/reports")

ALLOWED_VIEWS = {
    "dashboard",
    "generate",
    "templates",
    "scheduled",
    "history",
    "shared",
    "exports",
    "audit",
}


@bp.get("/")
def index():
    view = request.args.get("view", "dashboard")
    if view not in ALLOWED_VIEWS:
        view = "dashboard"
    payload = rv.build_module_payload()
    type_id = request.args.get("type", "")
    page = request.args.get("page", type=int)
    pager = None
    if view == "history":
        pager = paginate(payload["history"], page)
        payload = {**payload, "history": pager["items"]}
    elif view == "scheduled":
        pager = paginate(payload["scheduled"], page)
        payload = {**payload, "scheduled": pager["items"]}
    elif view == "shared":
        pager = paginate(payload["shared"], page)
        payload = {**payload, "shared": pager["items"]}
    elif view == "exports":
        pager = paginate(payload["exports"], page)
        payload = {**payload, "exports": pager["items"]}
    return render_template(
        "reports/index.html",
        active="reports",
        view=view,
        kpis=payload["kpis"],
        payload=payload,
        pager=pager,
        preselect_type=type_id if rv.get_report_type(type_id) else "",
    )


@bp.get("/preview")
def preview():
    type_id = request.args.get("type", "executive")
    if not rv.get_report_type(type_id):
        type_id = "executive"
    date_range = request.args.get("range", "30d")
    department = request.args.get("department", "")
    fmt = request.args.get("format", "PDF")
    report = rv.build_preview(type_id, date_range=date_range, department=department)
    return render_template(
        "reports/preview.html",
        active="reports",
        report=report,
        export_format=fmt,
        date_range=date_range,
        department=department,
    )


@bp.get("/export/<type_id>")
def export_report(type_id: str):
    if not rv.get_report_type(type_id):
        flash("Unknown report type.", "error")
        return redirect(url_for("reports.index", view="generate"))
    fmt = (request.args.get("format") or "csv").lower()
    rtype = rv.get_report_type(type_id)
    assert rtype is not None
    safe_name = rtype["name"].replace(" ", "_")

    if fmt in ("pdf", "word", "html", "print"):
        # Printable HTML — user can Save as PDF from the browser
        return redirect(
            url_for(
                "reports.preview",
                type=type_id,
                format=fmt.upper() if fmt != "print" else "PDF",
                range=request.args.get("range", "30d"),
                department=request.args.get("department", ""),
                print=1,
            )
        )

    if fmt == "json":
        body = rv.to_json(type_id)
        return Response(
            body,
            mimetype="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'},
        )

    # CSV (also used for Excel-compatible download)
    body = rv.to_csv(type_id)
    ext = "csv"
    mime = "text/csv"
    if fmt in ("excel", "xlsx", "xls"):
        ext = "csv"
        mime = "text/csv"
        safe_name = f"{safe_name}_Excel"
    return Response(
        body,
        mimetype=mime,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.{ext}"'},
    )


@bp.route("/create", methods=["GET", "POST"])
def create():
    return redirect(url_for("reports.index", view="generate"))


@bp.get("/<int:item_id>")
def details(item_id: int):
    # History item → open matching preview (demo: map id to history row)
    history = rv.report_history()
    row = next((h for h in history if h["id"] == item_id), None)
    if row:
        return redirect(url_for("reports.preview", type=row["type_id"], format=row["format"]))
    return redirect(url_for("reports.index", view="history"))

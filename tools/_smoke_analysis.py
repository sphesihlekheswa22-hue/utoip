import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app

with app.app_context():
    from uitop.services.analysis_view import build_module_payload

    p = build_module_payload()
    print("score", p["kpis"]["infrastructure_score"])
    print("insights", len(p["ai_insights"]), "forecasts", len(p["forecasts"]))

c = app.test_client()
c.post("/login", data={"email": "admin@example.com", "password": "Admin@UITOP2026"})
for path in [
    "/analysis/",
    "/analysis/?view=infrastructure",
    "/analysis/?view=assets",
    "/analysis/?view=helpdesk",
    "/analysis/?view=financial",
    "/analysis/?view=forecasts",
    "/analysis/?view=reports",
    "/analytics/",
]:
    r = c.get(path, follow_redirects=True)
    print(path, r.status_code, len(r.data))

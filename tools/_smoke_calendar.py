import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app

with app.app_context():
    from uitop.services.calendar_view import collect_events, calendar_kpis

    ev = collect_events()
    print("events", len(ev))
    types = {}
    for e in ev:
        types[e["type"]] = types.get(e["type"], 0) + 1
    print(types)
    print(calendar_kpis(ev))

c = app.test_client()
c.post("/login", data={"email": "admin@umzinyathi.gov.za", "password": "Admin@UITOP2026"})
for path in ["/calendar/", "/calendar/?view=week", "/calendar/?view=agenda", "/calendar/?view=timeline"]:
    r = c.get(path)
    print(path, r.status_code, len(r.data))

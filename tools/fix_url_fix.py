from pathlib import Path

ROOT = Path(r"C:\Users\Zoey\OneDrive\Documents\My Web Apps\NewUITOP\templates")
MODULE = [
    "software",
    "licenses",
    "vendors",
    "knowledge",
    "maintenance",
    "documents",
    "roles",
    "departments",
    "calendar",
    "security",
    "profile",
]

for mod in MODULE:
    for name in ("create.html", "edit.html"):
        p = ROOT / mod / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        old = f"url_for('{mod}.index')"
        new = f"url_for('modules.{mod}_index')"
        if old in t:
            p.write_text(t.replace(old, new), encoding="utf-8")
            print("fixed", p.relative_to(ROOT))
        else:
            print("ok", p.relative_to(ROOT))

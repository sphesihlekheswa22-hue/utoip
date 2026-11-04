"""Run initial seed only when the database has no users (Render build / manual)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    from uitop import create_app
    from uitop.models.user import User
    from uitop.seeds.bootstrap import run_seed

    app = create_app("production")
    light = os.getenv("RENDER_LIGHT_SEED", "true").lower() in {"1", "true", "yes"}
    with app.app_context():
        count = User.query.count()
        if count > 0:
            print(f"Database already has {count} user(s); skipping seed.")
            return 0
        print("Empty database — running initial seed…")
        run_seed(sample_inventory=not light)
        print("Seed completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

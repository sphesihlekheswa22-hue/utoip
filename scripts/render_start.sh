#!/usr/bin/env bash
# Free-tier Render: no preDeployCommand or Shell — migrate and seed before gunicorn.
set -euo pipefail

flask db upgrade

python - <<'PY'
from uitop import create_app
from uitop.models.user import User
from uitop.seeds.bootstrap import run_seed

app = create_app("production")
with app.app_context():
    if User.query.count() == 0:
        run_seed()
        print("Initial database seed completed.")
    else:
        print("Database already seeded; skipping.")
PY

exec gunicorn wsgi:app --bind "0.0.0.0:${PORT}" --workers 2 --timeout 120

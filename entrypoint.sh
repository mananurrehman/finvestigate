#!/bin/bash
# entrypoint.sh - runs inside container before Flask starts
set -e

echo "=========================================="
echo "Finvestigate Container Starting..."
echo "=========================================="

# ========== WAIT FOR DATABASE ==========
echo "Waiting for database..."
while ! python -c "
try:
    from app import create_app, db
    app = create_app('production')
    with app.app_context():
        db.engine.connect()
except Exception as e:
    print('Not ready:', e)
    exit(1)
" 2>/dev/null; do
    echo "Database not ready, retrying in 3 seconds..."
    sleep 3
done
echo "Database connected!"

# ========== RUN MIGRATIONS ==========
echo "Running migrations..."
python -c "
import os
from app import create_app, db
from flask_migrate import upgrade

app = create_app('production')
with app.app_context():
    if os.path.exists('migrations'):
        upgrade()
        print('Migrations applied!')
    else:
        db.create_all()
        print('Tables created (no migrations folder)')
"

# ========== START FLASK ==========
echo "Starting Flask..."
echo "=========================================="
exec python run.py
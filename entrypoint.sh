#!/bin/bash
# entrypoint.sh
# Runs INSIDE container before Flask starts

set -e

echo "=========================================="
echo "🚀 Finvestigate Container Starting..."
echo "=========================================="

# ========== WAIT FOR DATABASE ==========
echo "⏳ Waiting for database..."
while ! python -c "
try:
    from app import create_app
    from app.extensions import db
    app = create_app('production')
    with app.app_context():
        db.engine.connect()
        print('connected')
except Exception:
    exit(1)
" 2>/dev/null; do
    echo "⏳ Database not ready, retrying in 3 seconds..."
    sleep 3
done
echo "✅ Database connected!"

# ========== RUN MIGRATIONS ==========
echo "🗄️ Running migrations..."
python -c "
try:
    from app import create_app
    from flask_migrate import upgrade
    import os

    app = create_app('production')
    with app.app_context():
        if os.path.exists('migrations'):
            upgrade()
            print('✅ Migrations applied!')
        else:
            from app.extensions import db
            db.create_all()
            print('✅ Tables created (no migrations folder)')
except Exception as e:
    print(f'⚠️ Migration note: {e}')
"

# ========== START FLASK ==========
echo "🌐 Starting Flask..."
echo "=========================================="
exec python run.py
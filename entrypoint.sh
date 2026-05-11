#!/bin/bash
set -e

echo "Waiting for MySQL to be ready..."
# Wait for MySQL to accept connections
while ! python -c "
import pymysql
try:
    pymysql.connect(host='${DB_HOST}', port=int('${DB_PORT}'), user='${DB_USERNAME}', password='${DB_PASS}', database='${DB_NAME}')
    print('MySQL is ready!')
except Exception as e:
    print(f'Waiting... {e}')
    exit(1)
" 2>/dev/null; do
    sleep 2
done

echo "Running database migrations..."
flask db migrate -m "auto" || true
flask db upgrade || true

echo "Starting gunicorn..."
exec gunicorn --config gunicorn-cfg.py run:app

#!/bin/sh
# Render's dockerCommand field does naive whitespace-splitting and doesn't
# respect quotes, so "sh -c '...'" one-liners get mangled. Keep it here
# instead, referenced as a single no-spaces token in render.yaml.
set -e
python manage.py migrate --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3

#!/bin/sh
exec gunicorn --preload wsgi:app --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120

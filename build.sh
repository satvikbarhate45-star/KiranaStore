#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "--- INSTALLING PYTHON DEPENDENCIES ---"
pip install -r requirements.txt

echo "--- COLLECTING STATIC ASSETS ---"
python manage.py collectstatic --no-input

echo "--- RUNNING DATABASE MIGRATIONS ON SUPABASE ---"
python manage.py migrate

echo "--- BUILD COMPLETED SUCCESSFULLY ---"

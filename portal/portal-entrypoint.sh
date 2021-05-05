#!/bin/sh 
echo "Running db migrations ..."
python manage.py db upgrade
echo "db migrations ran successfully"
echo "\nStarting webserver\n"
gunicorn manage:app --bind 0.0.0.0:8080

mig:
	python manage.py makemigrations
	python manage.py migrate

run:
	DJANGO_SETTINGS_MODULE=root.settings celery -A apps worker --loglevel=info
admin:
	python manage.py createsuperuser


.PHONY: install migrate run seed test worker beat lint

install:
	python -m venv .venv && .venv/bin/pip install -r requirements.txt

migrate:
	python manage.py makemigrations && python manage.py migrate

run:
	python manage.py runserver 8000

seed:
	python manage.py seed_demo --email demo@licenseguard.local --password DemoPassw0rd!

test:
	python manage.py test

worker:
	celery -A config worker -l info

beat:
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

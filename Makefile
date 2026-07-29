run:
	uvicorn app.main:app --reload --reload-dir app

db:
	psql plan_b

initdb:
	python3 -m app.init_db

test-tourapi:
	python3 -m app.test.test_tourapi

test-google:
	python3 -m app.test.test_google_places

test-repo:
	python3 -m app.test.test_repository

format:
	black app/

lint:
	ruff check app/

typecheck:
	mypy app/

check: format lint typecheck
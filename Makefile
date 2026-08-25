install:
	pip install -e ".[test]"

run:
	uvicorn src.interfaces.api.app:app --reload

test:
	pytest -q

lint:
	python -m compileall src entrypoint tests

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

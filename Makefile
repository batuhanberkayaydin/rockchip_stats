.PHONY: format lint test

format:
	autopep8 --in-place --aggressive --aggressive --recursive . --max-line-length 160 --exclude .tox,.venv,build

lint:
	flake8 .

test:
	tox


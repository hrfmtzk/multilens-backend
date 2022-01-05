all:	test

test: pep8 lint type unittest

pep8:
	flake8 multilens tests

lint:
	black --check multilens tests
	isort --check multilens tests

type:
	mypy multilens tests

unittest:
	pytest

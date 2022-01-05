all:	test

test: unittest lint type

unittest:
	pytest

lint:
	black --check multilens tests
	isort --check multilens tests

type:
	mypy multilens tests
